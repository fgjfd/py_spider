# 工具函数模块
# 提供通用的工具函数，如URL检查、图片尺寸获取、文件夹压缩等
import os
import json
import zipfile
from PIL import Image


def is_normal_url(url):
    """检查URL是否有效"""
    # 检查URL是否存在且包含http或https协议
    return url and ('http' in url or 'https' in url)


def get_image_dimensions(main_folder, comic_name):
    """获取所有图片的高宽并保存到JSON文件"""
    print("\n开始获取图片高宽信息...")
    start_time = time.time()
    
    # 创建存储尺寸信息的文件夹
    length_folder = os.path.join(main_folder, "length")
    if not os.path.exists(length_folder):
        os.makedirs(length_folder)
        print(f"创建length文件夹: {length_folder}")
    
    # 存储所有图片的尺寸信息
    all_dimensions = {}
    
    # 遍历主文件夹下的所有章节文件夹
    for chapter_name in sorted(os.listdir(main_folder), key=lambda x: int(x) if x.isdigit() else float('inf')):
        chapter_path = os.path.join(main_folder, chapter_name)
        
        # 只处理数字命名的文件夹，跳过length文件夹
        if os.path.isdir(chapter_path) and chapter_name != "length":
            all_dimensions[chapter_name] = {}
            
            # 遍历章节文件夹下的所有图片文件
            for img_file in os.listdir(chapter_path):
                if img_file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                    img_path = os.path.join(chapter_path, img_file)
                    try:
                        # 打开图片并获取尺寸
                        with Image.open(img_path) as img:
                            width, height = img.size
                            img_name = os.path.splitext(img_file)[0]
                            all_dimensions[chapter_name][img_name] = {
                                "height": height,
                                "width": width
                            }
                    except Exception as e:
                        print(f"获取图片 {img_file} 高宽失败: {e}")
    
    # 如果有尺寸信息，保存到JSON文件
    if all_dimensions:
        json_file_path = os.path.join(length_folder, "dimensions.json")
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(all_dimensions, f, ensure_ascii=False, indent=2)
        print(f"保存所有图片高宽信息到 {json_file_path}")
    
    end_time = time.time()
    print(f"创建JSON文件耗时: {end_time - start_time:.2f} 秒")


def zip_main_folder(main_folder, download_path=None):
    """将主文件夹压缩成ZIP文件"""
    print(f"\n开始压缩文件夹...")
    start_time = time.time()
    
    # 如果指定了下载路径，则使用指定路径，否则使用当前目录
    if download_path:
        main_folder = os.path.join(download_path, main_folder)
    
    # 压缩文件名
    zip_filename = os.path.join(download_path if download_path else ".", f"{os.path.basename(main_folder)}.zip")
    
    try:
        # 创建ZIP文件并添加所有文件
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(main_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, os.path.dirname(main_folder))
                    zipf.write(file_path, arcname)
                    print(f"已添加: {arcname}")
        
        end_time = time.time()
        print(f"压缩完成！文件保存为: {zip_filename}")
        print(f"压缩耗时: {end_time - start_time:.2f} 秒")
        
        # 计算并显示压缩文件大小
        file_size = os.path.getsize(zip_filename)
        file_size_mb = file_size / (1024 * 1024)
        print(f"压缩文件大小: {file_size_mb:.2f} MB")
        
    except Exception as e:
        print(f"压缩文件夹时出错: {e}")


# 导入必要的模块
import time
