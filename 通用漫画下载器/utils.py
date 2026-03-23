import os
import zipfile
from PIL import Image
import img2pdf
from concurrent.futures import ThreadPoolExecutor, as_completed

def is_normal_url(url):
    """检查URL是否有效"""
    return url and ('http' in url or 'https' in url)


def zip_main_folder(comic_name, base_path=None):
    """压缩主文件夹"""
    import shutil
    
    if base_path is None:
        base_path = os.getcwd()
    
    main_folder = os.path.join(base_path, comic_name)
    zip_file = os.path.join(base_path, f"{comic_name}.zip")
    
    print(f"\n正在压缩文件夹: {main_folder}")
    
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(main_folder):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, base_path)
                zipf.write(file_path, arcname)
    
    print(f"压缩完成: {zip_file}")
    
    print(f"已保留原文件夹: {main_folder}")


def get_sorted_images(folder_path):
    """获取文件夹中排序后的图片列表"""
    images = []
    for file in os.listdir(folder_path):
        if file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            images.append(os.path.join(folder_path, file))
    
    images.sort(key=lambda x: int(os.path.splitext(os.path.basename(x))[0]) 
                if os.path.splitext(os.path.basename(x))[0].isdigit() else 0)
    return images


def merge_images_to_long_images(image_paths, output_folder, chapter_name, max_height=60000):
    """
    将多张图片垂直拼接成长图，保存到指定文件夹
    
    Args:
        image_paths: 图片路径列表
        output_folder: 输出文件夹路径
        chapter_name: 章节名称
        max_height: 单张长图最大高度（像素）
    
    Returns:
        list: 生成的长图路径列表
    """
    if not image_paths:
        return []
    
    try:
        images = []
        max_width = 0
        
        for img_path in image_paths:
            img = Image.open(img_path)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            images.append(img)
            max_width = max(max_width, img.width)
        
        segments = []
        current_segment = []
        current_height = 0
        
        for img in images:
            if current_height + img.height > max_height and current_segment:
                segments.append(current_segment)
                current_segment = [img]
                current_height = img.height
            else:
                current_segment.append(img)
                current_height += img.height
        
        if current_segment:
            segments.append(current_segment)
        
        output_paths = []
        for seg_idx, seg_images in enumerate(segments, 1):
            total_height = sum(img.height for img in seg_images)
            merged = Image.new('RGB', (max_width, total_height), (255, 255, 255))
            
            y_offset = 0
            for img in seg_images:
                x_offset = (max_width - img.width) // 2
                merged.paste(img, (x_offset, y_offset))
                y_offset += img.height
            
            output_path = os.path.join(output_folder, f"{chapter_name}_{seg_idx}.jpg")
            merged.save(output_path, 'JPEG', quality=95)
            merged.close()
            output_paths.append(output_path)
        
        for img in images:
            img.close()
        
        return output_paths
    except Exception as e:
        print(f"拼接图片失败: {e}")
        return []


def images_to_pdf(image_paths, output_pdf_path):
    """
    将多张图片合并为一个分页PDF
    
    Args:
        image_paths: 图片路径列表
        output_pdf_path: 输出PDF路径
    
    Returns:
        bool: 是否成功
    """
    if not image_paths:
        return False
    
    try:
        with open(output_pdf_path, "wb") as f:
            f.write(img2pdf.convert(image_paths))
        return True
    except Exception as e:
        print(f"PDF转换失败: {e}")
        return False


def single_image_to_pdf(image_path, output_pdf_path):
    """将单张图片转换为PDF"""
    try:
        with open(output_pdf_path, "wb") as f:
            f.write(img2pdf.convert([image_path]))
        return True
    except Exception as e:
        print(f"PDF转换失败: {e}")
        return False


def process_chapter_pdf(args):
    """处理单个章节的PDF转换（用于多线程）"""
    chapter_name, chapter_path, pdf_folder, long_mode = args
    images = get_sorted_images(chapter_path)
    if not images:
        return chapter_name, False, "无图片"
    
    output_pdf = os.path.join(pdf_folder, f"{chapter_name}.pdf")
    if long_mode:
        temp_folder = os.path.join(pdf_folder, f"{chapter_name}_temp")
        os.makedirs(temp_folder, exist_ok=True)
        long_images = merge_images_to_long_images(images, temp_folder, chapter_name)
        if long_images:
            success = images_to_pdf(long_images, output_pdf)
            for img_path in long_images:
                if os.path.exists(img_path):
                    os.remove(img_path)
            if os.path.exists(temp_folder):
                os.rmdir(temp_folder)
            return chapter_name, success, f"长图模式 {len(images)}张"
        return chapter_name, False, "长图生成失败"
    else:
        success = images_to_pdf(images, output_pdf)
        return chapter_name, success, f"分页模式 {len(images)}张"


def process_chapter_long_image(args):
    """处理单个章节的长图转换（用于多线程）"""
    chapter_name, chapter_path, output_folder, max_height = args
    images = get_sorted_images(chapter_path)
    if not images:
        return chapter_name, [], "无图片"
    
    chapter_folder = os.path.join(output_folder, chapter_name)
    os.makedirs(chapter_folder, exist_ok=True)
    
    long_images = merge_images_to_long_images(images, chapter_folder, chapter_name, max_height)
    if long_images:
        return chapter_name, long_images, f"生成{len(long_images)}张长图"
    return chapter_name, [], "长图生成失败"


def process_single_image_pdf(args):
    """处理单张图片转PDF（用于多线程）"""
    img_path, output_pdf = args
    return single_image_to_pdf(img_path, output_pdf)


def convert_folder_to_pdf(folder_path, pdf_mode='per_chapter', long_mode=False, 
                          progress_callback=None, max_workers=4):
    """
    将文件夹中的图片转换为PDF（支持多线程）
    
    Args:
        folder_path: 文件夹路径
        pdf_mode: PDF模式
            - 'per_chapter': 每个子文件夹（章节）一个PDF
            - 'single': 每张图片单独转PDF
        long_mode: 是否使用长图模式（仅对per_chapter模式有效）
        progress_callback: 进度回调函数 callback(current, total, message)
        max_workers: 最大线程数
    
    Returns:
        tuple: (success_count, fail_count, pdf_folder)
    """
    if not os.path.exists(folder_path):
        print(f"文件夹不存在: {folder_path}")
        return 0, 0, None
    
    folder_name = os.path.basename(folder_path)
    parent_path = os.path.dirname(folder_path)
    pdf_folder = os.path.join(parent_path, f"{folder_name}_PDF")
    os.makedirs(pdf_folder, exist_ok=True)
    
    subfolders = []
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        if os.path.isdir(item_path):
            subfolders.append((item, item_path))
    
    if not subfolders:
        subfolders = [(folder_name, folder_path)]
        pdf_folder = parent_path
    
    subfolders.sort(key=lambda x: int(x[0]) if x[0].isdigit() else 0)
    
    success_count = 0
    fail_count = 0
    
    if pdf_mode == 'per_chapter':
        tasks = [(name, path, pdf_folder, long_mode) for name, path in subfolders]
        total = len(tasks)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_chapter_pdf, task): task for task in tasks}
            
            for idx, future in enumerate(as_completed(futures), 1):
                chapter_name, success, msg = future.result()
                if progress_callback:
                    progress_callback(idx, total, f"处理: {chapter_name} - {msg}")
                print(f"  {chapter_name}: {msg} {'成功' if success else '失败'}")
                
                if success:
                    success_count += 1
                else:
                    fail_count += 1
    
    elif pdf_mode == 'single':
        tasks = []
        for chapter_name, chapter_path in subfolders:
            images = get_sorted_images(chapter_path)
            chapter_pdf_folder = os.path.join(pdf_folder, chapter_name)
            os.makedirs(chapter_pdf_folder, exist_ok=True)
            
            for img_path in images:
                img_name = os.path.splitext(os.path.basename(img_path))[0]
                output_pdf = os.path.join(chapter_pdf_folder, f"{img_name}.pdf")
                tasks.append((img_path, output_pdf))
        
        total = len(tasks)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_single_image_pdf, task): task for task in tasks}
            
            for idx, future in enumerate(as_completed(futures), 1):
                success = future.result()
                if progress_callback:
                    task = futures[future]
                    img_name = os.path.splitext(os.path.basename(task[0]))[0]
                    progress_callback(idx, total, f"转换: {img_name}.pdf")
                
                if success:
                    success_count += 1
                else:
                    fail_count += 1
    
    print(f"\nPDF生成完成，保存在: {pdf_folder}")
    print(f"成功: {success_count}, 失败: {fail_count}")
    return success_count, fail_count, pdf_folder


def convert_folder_to_long_images(folder_path, max_height=60000, progress_callback=None, max_workers=4):
    """
    将文件夹中的图片转换为长图（支持多线程）
    每章的长图保存到对应文件夹（如 1, 2, 3...）
    
    Args:
        folder_path: 文件夹路径
        max_height: 单张长图最大高度
        progress_callback: 进度回调函数
        max_workers: 最大线程数
    
    Returns:
        tuple: (success_count, fail_count, output_folder)
    """
    if not os.path.exists(folder_path):
        print(f"文件夹不存在: {folder_path}")
        return 0, 0, None
    
    folder_name = os.path.basename(folder_path)
    parent_path = os.path.dirname(folder_path)
    output_folder = os.path.join(parent_path, f"{folder_name}_长图")
    os.makedirs(output_folder, exist_ok=True)
    
    subfolders = []
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        if os.path.isdir(item_path):
            subfolders.append((item, item_path))
    
    if not subfolders:
        subfolders = [(folder_name, folder_path)]
    
    subfolders.sort(key=lambda x: int(x[0]) if x[0].isdigit() else 0)
    
    success_count = 0
    fail_count = 0
    
    tasks = [(name, path, output_folder, max_height) for name, path in subfolders]
    total = len(tasks)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_chapter_long_image, task): task for task in tasks}
        
        for idx, future in enumerate(as_completed(futures), 1):
            chapter_name, long_images, msg = future.result()
            if progress_callback:
                progress_callback(idx, total, f"处理: {chapter_name} - {msg}")
            print(f"  {chapter_name}: {msg}")
            
            if long_images:
                success_count += 1
            else:
                fail_count += 1
    
    print(f"\n长图生成完成，保存在: {output_folder}")
    print(f"成功: {success_count}, 失败: {fail_count}")
    return success_count, fail_count, output_folder


def convert_comic_to_pdf(comic_name, base_path, pdf_mode='per_chapter', long_mode=False, max_workers=4):
    """
    将漫画转换为PDF（支持多线程）
    
    Args:
        comic_name: 漫画名称
        base_path: 基础路径
        pdf_mode: PDF模式
            - 'per_chapter': 每个章节一个PDF
            - 'single': 每张图片单独转PDF
        long_mode: 是否使用长图模式
        max_workers: 最大线程数
    """
    main_folder = os.path.join(base_path, comic_name)
    if not os.path.exists(main_folder):
        print(f"文件夹不存在:{main_folder}")
        return False
    
    success, fail, _ = convert_folder_to_pdf(main_folder, pdf_mode, long_mode, max_workers=max_workers)
    return success > 0
