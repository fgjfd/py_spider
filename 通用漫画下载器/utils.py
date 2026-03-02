import os
import json
import zipfile
import time
from PIL import Image


def is_normal_url(url):
    """检查URL是否有效"""
    return url and ('http' in url or 'https' in url)


def get_image_dimensions(comic_name, base_path=None):
    """获取所有图片的尺寸并保存到dimensions.json"""
    if base_path is None:
        base_path = os.getcwd()
    
    main_folder = os.path.join(base_path, comic_name)
    print(f"\n正在获取图片尺寸: {main_folder}")
    
    length_folder = os.path.join(main_folder, "length")
    if not os.path.exists(length_folder):
        os.makedirs(length_folder)
    
    dimensions = {}
    failed_images = []
    
    cover_folder = os.path.join(main_folder, "0")
    if os.path.exists(cover_folder) and os.path.isdir(cover_folder):
        dimensions["0"] = {}
        cover_path = os.path.join(cover_folder, "cover.jpg")
        if os.path.exists(cover_path):
            try:
                with Image.open(cover_path) as img:
                    width, height = img.size
                    dimensions["0"]["cover"] = {
                        "width": width,
                        "height": height
                    }
            except Exception as e:
                print(f"获取封面尺寸失败 {cover_path}: {e}")
                dimensions["0"]["cover"] = {
                    "width": 0,
                    "height": 0
                }
                failed_images.append("0/cover.jpg")
    
    for chapter_folder in os.listdir(main_folder):
        chapter_path = os.path.join(main_folder, chapter_folder)
        
        if not os.path.isdir(chapter_path) or chapter_folder == "length" or chapter_folder == "0":
            continue
        
        chapter_num = chapter_folder
        dimensions[chapter_num] = {}
        
        image_files = [f for f in os.listdir(chapter_path) if f.endswith('.jpg')]
        
        for image_file in image_files:
            img_num = image_file.split('.')[0]
            image_path = os.path.join(chapter_path, image_file)
            try:
                with Image.open(image_path) as img:
                    width, height = img.size
                    dimensions[chapter_num][img_num] = {
                        "width": width,
                        "height": height
                    }
            except Exception as e:
                print(f"获取图片尺寸失败 {image_path}: {e}")
                dimensions[chapter_num][img_num] = {
                    "width": 0,
                    "height": 0
                }
                failed_images.append(f"{chapter_num}/{image_file}")
    
    json_file_path = os.path.join(length_folder, "dimensions.json")
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(dimensions, f, ensure_ascii=False, indent=2)
    
    print(f"图片尺寸已保存到: {json_file_path}")
    
    if failed_images:
        print(f"\n⚠️  注意：以下图片可能存在问题:")
        for img in failed_images:
            print(f"  - {img}")
    
    return dimensions


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
