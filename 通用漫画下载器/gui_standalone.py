# 可视化界面模块 - 通用版（完全独立）
# 使用tkinter创建图形用户界面，整合漫画下载功能
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from DrissionPage import ChromiumOptions, ChromiumPage
from urllib.parse import urlparse, unquote
import asyncio
import threading
import os
import re
import json
import aiofiles
import aiohttp
import zipfile
from PIL import Image
import time

# ========== 配置部分 ==========
# 快看配置
KUAICAN_CONFIG = {
    "COMIC_SITE_URL": "https://www.kuaikanmanhua.com/",
    "BROWSER_PATH": r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "XPATHS": {
        "search_input": "/html/body/div[1]/div/div/div/div[1]/div[2]/div/div[1]/input",
        "search_button": "/html/body/div[1]/div/div/div/div[1]/div[2]/div/div[1]/a",
        "search_result": "/html/body/div[1]/div/div/div/div[3]/div[1]/div[1]/div[1]/a/div[1]/img[1]",
        "cover_image": "/html/body/div[1]/div/div/div/div[2]/div/div[1]/div/div[1]/img[3]",
        "chapter_list": "/html/body/div[1]/div/div/div/div[2]/div/div[2]/div[1]/div[1]/div/div[3]/div",
        "chapter_group_button": "/html/body/div[1]/div/div/div/div[2]/div/div[2]/div[1]/div[1]/div/div[2]/div",
        "chapter_image_parent": "/html/body/div[1]/div/div/div/div[4]/div[1]/div[1]/div",
        "chapter_image": "/html/body/div[1]/div/div/div/div[4]/div[1]/div[1]/div[num]/img"
    }
}

# 好多漫配置
HAODUOMAN_CONFIG = {
    "COMIC_SITE_URL": "https://www.haoduoman.com/",
    "BROWSER_PATH": r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "XPATHS": {
        "search_input": "/html/body/header/div[2]/div/div[2]/div/form/div/p[1]/input",
        "search_button": "/html/body/header/div[2]/div/div[2]/div/form/div/p[2]/button",
        "search_result": "/html/body/main/div/div[2]/div/div[1]/div/div/div[2]/a",
        "cover_image": "/html/body/main/div/div[2]/div[1]/div/div/div/div[1]/img",
        "chapter_list": "/html/body/main/div/div[3]/div[2]/ul/li",
        "chapter_link": "/html/body/main/div/div[3]/div[2]/ul/li[num]/a",
        "chapter_image_parent": "/html/body/main/div[1]/div/div[1]/div",
        "chapter_image_data_original": "/html/body/main/div[1]/div/div[1]/div[num]"
    }
}

# 通用配置
GENERAL_CONFIG = {
    "MAX_RETRIES": 5,
    "MAX_RETRY": 3,
    "WAIT_TIME": 0.1,
    "MAX_THREADS": 3,
    "CONCURRENT_DOWNLOAD_LIMIT": 10,
    "DOWNLOAD_DELAY": 0.2
}


# ========== 工具函数 ==========
def is_normal_url(url):
    """检查URL是否有效"""
    return url and ('http' in url or 'https' in url)


def get_image_dimensions(main_folder):
    """获取所有图片的高宽并保存到JSON文件"""
    print("\n开始获取图片高宽信息...")
    start_time = time.time()
    
    length_folder = os.path.join(main_folder, "length")
    if not os.path.exists(length_folder):
        os.makedirs(length_folder)
        print(f"创建length文件夹: {length_folder}")
    
    all_dimensions = {}
    
    for chapter_name in sorted(os.listdir(main_folder), key=lambda x: int(x) if x.isdigit() else float('inf')):
        chapter_path = os.path.join(main_folder, chapter_name)
        
        if os.path.isdir(chapter_path) and chapter_name != "length":
            all_dimensions[chapter_name] = {}
            
            for img_file in os.listdir(chapter_path):
                if img_file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                    img_path = os.path.join(chapter_path, img_file)
                    try:
                        with Image.open(img_path) as img:
                            width, height = img.size
                            img_name = os.path.splitext(img_file)[0]
                            all_dimensions[chapter_name][img_name] = {
                                "height": height,
                                "width": width
                            }
                    except Exception as e:
                        print(f"获取图片 {img_file} 高宽失败: {e}")
    
    if all_dimensions:
        json_file_path = os.path.join(length_folder, "dimensions.json")
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(all_dimensions, f, ensure_ascii=False, indent=2)
        print(f"保存所有图片高宽信息到 {json_file_path}")
    
    end_time = time.time()
    print(f"创建JSON文件耗时: {end_time - start_time:.2f} 秒")


def zip_main_folder(comic_name, base_path=None):
    """压缩主文件夹为ZIP文件"""
    if base_path is None:
        base_path = os.getcwd()
    
    main_folder = os.path.join(base_path, comic_name)
    zip_file_path = os.path.join(base_path, f"{comic_name}.zip")
    
    print(f"\n开始压缩文件夹: {main_folder}")
    start_time = time.time()
    
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(main_folder):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, base_path)
                zipf.write(file_path, arcname)
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"文件夹压缩成功: {zip_file_path}")
    print(f"压缩耗时: {elapsed_time:.2f} 秒")


# ========== 下载函数 ==========
async def async_download_image(session, url, i, folder_name, progress_callback=None, max_retries=3):
    """异步下载单张图片"""
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    file_path = os.path.join(folder_name, f"{i}.jpg")
                    content = await response.read()
                    async with aiofiles.open(file_path, 'wb') as f:
                        await f.write(content)
                    if progress_callback:
                        progress_callback(len(content))
                    print(f"下载成功: {file_path}")
                    return
                else:
                    last_error = f"下载失败 (状态码: {response.status}): {url}"
        except Exception as e:
            last_error = f"下载第{i}张图片时出错: {e}"
        
        retry_count += 1
    
    print(last_error)


async def async_download_images(herf_list, folder_name, progress_callback=None):
    """异步方式下载图片到指定文件夹，文件名按序号命名"""
    print(f"\n开始下载图片到 {folder_name} (异步方式)...")
    start_time = time.time()
    
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    
    connector = aiohttp.TCPConnector(limit=GENERAL_CONFIG["CONCURRENT_DOWNLOAD_LIMIT"])
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for i, herf in enumerate(herf_list, 1):
            task = async_download_image(session, herf, i, folder_name, progress_callback)
            tasks.append(task)
            if i % GENERAL_CONFIG["CONCURRENT_DOWNLOAD_LIMIT"] == 0:
                await asyncio.gather(*tasks)
                tasks = []
                await asyncio.sleep(GENERAL_CONFIG["DOWNLOAD_DELAY"])
        
        if tasks:
            await asyncio.gather(*tasks)
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"{folder_name} 下载完成")
    print(f"下载耗时: {elapsed_time:.2f} 秒")


async def download_all_chapters(all_chapters_data, comic_name, base_path=None, progress_callback=None):
    """下载所有章节的图片"""
    if base_path is None:
        base_path = os.getcwd()
    
    main_folder = os.path.join(base_path, comic_name)
    if not os.path.exists(main_folder):
        os.makedirs(main_folder)
    
    print(f"\n开始协程下载所有章节图片...")
    all_start_time = time.time()
    
    for chapter_data in all_chapters_data:
        chapter_num = chapter_data['chapter_num']
        herf_list = chapter_data['herf_list']
        
        if herf_list:
            folder_name = os.path.join(main_folder, str(chapter_num))
            await async_download_images(herf_list, folder_name, progress_callback)
    
    all_end_time = time.time()
    all_elapsed_time = all_end_time - all_start_time
    print(f"\n所有章节图片下载完成")
    print(f"总耗时: {all_elapsed_time:.2f} 秒")


async def async_download_cover_image(url, comic_name, base_path=None):
    """异步下载封面图片到0文件夹"""
    if base_path is None:
        base_path = os.getcwd()
    
    main_folder = os.path.join(base_path, comic_name)
    if not os.path.exists(main_folder):
        os.makedirs(main_folder)
    
    folder_0 = os.path.join(main_folder, "0")
    if not os.path.exists(folder_0):
        os.makedirs(folder_0)
    
    file_path = os.path.join(folder_0, "cover.jpg")
    
    old_cover_path = os.path.join(main_folder, "cover.jpg")
    if os.path.exists(old_cover_path):
        try:
            os.remove(old_cover_path)
            print(f"已删除大文件夹下的旧封面: {old_cover_path}")
        except Exception as e:
            print(f"删除旧封面失败: {e}")
    
    print(f"\n开始下载封面图片到0文件夹...")
    start_time = time.time()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.read()
                    async with aiofiles.open(file_path, 'wb') as f:
                        await f.write(content)
                    print(f"封面下载成功: {file_path}")
                else:
                    print(f"封面下载失败 (状态码: {response.status}): {url}")
    except Exception as e:
        print(f"下载封面图片时出错: {e}")
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"封面下载耗时: {elapsed_time:.2f} 秒")


async def download_cover_image(url, comic_name, base_path=None):
    """下载封面图片"""
    await async_download_cover_image(url, comic_name, base_path)


# ========== 快看爬虫函数 ==========
def kuaikan_get_chapter_image_urls(chapter_tab, max_img_num):
    """快看：获取单个章节的图片URL列表"""
    herf_list = []
    XPATHS = KUAICAN_CONFIG["XPATHS"]
    
    print("开始获取图片URL...")
    
    for num in range(1, max_img_num + 1):
        try:
            img_xpath = XPATHS['chapter_image'].replace("num", str(num))
            img_ele = chapter_tab.ele(f"xpath:{img_xpath}", timeout=3)
            herf = img_ele.attr("data-src")
            
            if is_normal_url(herf):
                print(f"第{num}张图片: {herf}")
                herf_list.append(herf)
            else:
                print(f"第{num}张图片URL无效: {herf}")
                
        except Exception as e:
            print(f"获取第{num}张图片时出错: {e}")
    
    return herf_list


def kuaikan_collect_chapter_images(chapter_info):
    """快看：收集单个章节的图片URL"""
    chapter_num = chapter_info['chapter_num']
    chapter_tab = chapter_info['tab']
    XPATHS = KUAICAN_CONFIG["XPATHS"]
    
    print(f"正在处理章节{chapter_num}")
    
    try:
        time.sleep(GENERAL_CONFIG["WAIT_TIME"] * 2)
        
        img_elements = chapter_tab.eles("xpath:" + XPATHS['chapter_image_parent'])
        max_img_num = len(img_elements)
        print(f"章节{chapter_num}检测到{max_img_num}张图片")
        
        herf_list = kuaikan_get_chapter_image_urls(chapter_tab, max_img_num)
        
    except Exception as e:
        print(f"处理章节{chapter_num}时出错: {e}")
        herf_list = []
    
    chapter_tab.close()
    
    return {
        'chapter_num': chapter_num,
        'herf_list': herf_list
    }


def kuaikan_click_chapter_group(target_comic_tab, group_index):
    """快看：点击章节组按钮"""
    XPATHS = KUAICAN_CONFIG["XPATHS"]
    try:
        group_button_xpath = f"{XPATHS['chapter_group_button']}[{group_index}]"
        group_button = target_comic_tab.ele(f"xpath:{group_button_xpath}")
        group_button.click()
        time.sleep(0.5)
        print(f"点击第{group_index}组按钮")
        return True
    except Exception as e:
        print(f"点击第{group_index}组按钮失败: {e}")
        return False


def kuaikan_collect_chapters_images(target_comic_tab, comic_num):
    """快看：多线程收集所有章节的图片URL"""
    XPATHS = KUAICAN_CONFIG["XPATHS"]
    print(f"设置最大同时收集线程数: {GENERAL_CONFIG['MAX_THREADS']}")

    chapter_list_xpath = XPATHS['chapter_list']
    
    # 先获取所有分组，计算总章节数
    # 点击最后一个分组来获取总章节数
    group_button_xpath = XPATHS['chapter_group_button']
    group_buttons = target_comic_tab.eles("xpath:" + group_button_xpath)
    total_groups = len(group_buttons)
    print(f"发现 {total_groups} 个章节分组")
    
    # 获取总章节数：点击最后一组，获取该组的章节数量
    if total_groups > 0:
        kuaikan_click_chapter_group(target_comic_tab, total_groups)
        time.sleep(0.5)
        chapter_eles = target_comic_tab.eles("xpath:" + chapter_list_xpath)
        chapters_in_last_group = len(chapter_eles)
        all_chapters_num = (total_groups - 1) * 50 + chapters_in_last_group
        print(f"总章节数: {all_chapters_num} (前{total_groups-1}组各50章，最后一组{chapters_in_last_group}章)")
        # 回到第一组开始下载
        kuaikan_click_chapter_group(target_comic_tab, 1)
        time.sleep(0.5)
    else:
        chapter_eles = target_comic_tab.eles("xpath:" + chapter_list_xpath)
        all_chapters_num = len(chapter_eles)
        print(f"总章节数: {all_chapters_num}")

    actual_comic_num = min(comic_num, all_chapters_num)
    print(f"用户请求下载 {comic_num} 章，实际可下载 {actual_comic_num} 章")

    all_chapters_data = []
    current_chapter = 1

    while current_chapter <= actual_comic_num:
        group_index = (current_chapter - 1) // 50 + 1
        kuaikan_click_chapter_group(target_comic_tab, group_index)
        time.sleep(0.3)
        
        chapter_eles = target_comic_tab.eles("xpath:" + chapter_list_xpath)
        chapters_in_group = len(chapter_eles)
        
        group_end = min(current_chapter + GENERAL_CONFIG['MAX_THREADS'] - 1, actual_comic_num)
        group_end = min(group_end, (group_index - 1) * 50 + chapters_in_group)
        
        print(f"\n处理第{group_index}组，章节范围: {current_chapter}-{group_end}")

        batch_chapters_info = []
        for num in range(current_chapter, group_end + 1):
            try:
                chapter_index_in_group = (num - 1) % 50 + 1
                chapter_xpath = f"{chapter_list_xpath}[{chapter_index_in_group}]"
                chapter_ele = target_comic_tab.ele(f"xpath:{chapter_xpath}")
                chapter_tab = chapter_ele.click.for_new_tab()

                batch_chapters_info.append({
                    'chapter_num': num,
                    'tab': chapter_tab
                })

                print(f"打开第{num}章节")

            except Exception as e:
                print(f"打开第{num}章节时出错: {e}")

        threads = []
        results = []

        def thread_wrapper(chapter_info):
            result = kuaikan_collect_chapter_images(chapter_info)
            results.append(result)

        for chapter_info in batch_chapters_info:
            thread = threading.Thread(target=thread_wrapper, args=(chapter_info,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        all_chapters_data.extend(results)
        current_chapter = group_end + 1

    return all_chapters_data


# ========== 好多漫爬虫函数 ==========
def haoduoman_get_chapter_image_urls(chapter_tab, max_img_num):
    """好多漫：获取单个章节的图片URL列表"""
    herf_list = []
    XPATHS = HAODUOMAN_CONFIG["XPATHS"]
    
    print("开始获取图片URL...")
    
    for num in range(1, max_img_num + 1):
        try:
            div_xpath = XPATHS['chapter_image_data_original'].replace("num", str(num))
            div_ele = chapter_tab.ele(f"xpath:{div_xpath}", timeout=3)
            herf = div_ele.attr("data-original")
            
            if is_normal_url(herf):
                print(f"第{num}张图片: {herf}")
                herf_list.append(herf)
            else:
                print(f"第{num}张图片URL无效: {herf}")
                
        except Exception as e:
            print(f"获取第{num}张图片时出错: {e}")
    
    return herf_list


def haoduoman_collect_chapter_images(chapter_info):
    """好多漫：收集单个章节的图片URL"""
    chapter_num = chapter_info['chapter_num']
    chapter_url = chapter_info['url']
    main_tab = chapter_info['main_tab']
    XPATHS = HAODUOMAN_CONFIG["XPATHS"]
    
    print(f"正在处理章节{chapter_num}: {chapter_url}")
    
    try:
        chapter_tab = main_tab.new_tab(chapter_url)
        time.sleep(GENERAL_CONFIG["WAIT_TIME"] * 2)
        
        img_elements = chapter_tab.eles("xpath:" + XPATHS['chapter_image_parent'])
        max_img_num = len(img_elements)
        print(f"章节{chapter_num}检测到{max_img_num}张图片")
        
        herf_list = haoduoman_get_chapter_image_urls(chapter_tab, max_img_num)
        
        chapter_tab.close()
        
    except Exception as e:
        print(f"处理章节{chapter_num}时出错: {e}")
        herf_list = []
    
    return {
        'chapter_num': chapter_num,
        'herf_list': herf_list
    }


def haoduoman_collect_chapters_images(target_comic_tab, comic_num, main_tab):
    """好多漫：多线程收集所有章节的图片URL"""
    XPATHS = HAODUOMAN_CONFIG["XPATHS"]
    COMIC_SITE_URL = HAODUOMAN_CONFIG["COMIC_SITE_URL"]
    
    print(f"设置最大同时收集线程数: {GENERAL_CONFIG['MAX_THREADS']}")
    
    chapter_list_xpath = XPATHS['chapter_list']
    chapter_eles = target_comic_tab.eles("xpath:" + chapter_list_xpath)
    all_chapters_num = len(chapter_eles)
    print(f"总章节数: {all_chapters_num}")
    
    first_chapter_xpath = XPATHS['chapter_link'].replace("num", "1")
    first_chapter_ele = target_comic_tab.ele(f"xpath:{first_chapter_xpath}", timeout=5)
    first_chapter_href = first_chapter_ele.attr("href")
    print(f"第一个章节链接: {first_chapter_href}")
    
    actual_comic_num = min(comic_num, all_chapters_num)
    print(f"用户请求下载 {comic_num} 章，实际可下载 {actual_comic_num} 章")
    
    all_chapters_data = []
    current_chapter = 1
    
    while current_chapter <= actual_comic_num:
        group_end = min(current_chapter + GENERAL_CONFIG['MAX_THREADS'] - 1, actual_comic_num)
        print(f"\n处理章节范围: {current_chapter}-{group_end}")
        
        batch_chapters_info = []
        for num in range(current_chapter, group_end + 1):
            chapter_url = re.sub(r'/\d+\.html$', f'/{num}.html', first_chapter_href)
            
            batch_chapters_info.append({
                'chapter_num': num,
                'url': chapter_url,
                'main_tab': main_tab
            })
            
            print(f"准备处理第{num}章节: {chapter_url}")
        
        threads = []
        results = []
        
        def thread_wrapper(chapter_info):
            result = haoduoman_collect_chapter_images(chapter_info)
            results.append(result)
        
        for chapter_info in batch_chapters_info:
            thread = threading.Thread(target=thread_wrapper, args=(chapter_info,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        all_chapters_data.extend(results)
        current_chapter = group_end + 1
    
    return all_chapters_data


# ========== GUI类 ==========
class ComicDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("通用漫画下载器")
        self.root.geometry("680x800")
        self.root.resizable(True, True)
        
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.title_label = ttk.Label(
            self.main_frame, 
            text="通用漫画下载器", 
            font=("微软雅黑", 16, "bold")
        )
        self.title_label.pack(pady=10)
        
        self.input_frame = ttk.LabelFrame(self.main_frame, text="下载设置", padding="10")
        self.input_frame.pack(fill=tk.X, pady=5)
        
        self.site_frame = ttk.Frame(self.input_frame)
        self.site_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.site_frame, text="选择网站:", width=10).pack(side=tk.LEFT, padx=5)
        self.site_var = tk.StringVar(value="快看")
        site_combobox = ttk.Combobox(
            self.site_frame,
            textvariable=self.site_var,
            values=["快看", "好多漫"],
            state="readonly",
            font=("微软雅黑", 10),
            width=15
        )
        site_combobox.pack(side=tk.LEFT, padx=5)
        
        self.name_frame = ttk.Frame(self.input_frame)
        self.name_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.name_frame, text="漫画名称:", width=10).pack(side=tk.LEFT, padx=5)
        self.comic_name_var = tk.StringVar()
        self.comic_name_entry = ttk.Entry(
            self.name_frame, 
            textvariable=self.comic_name_var, 
            font=("微软雅黑", 10)
        )
        self.comic_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.cookie_frame = ttk.Frame(self.input_frame)
        self.cookie_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.cookie_frame, text="Cookie:", width=10).pack(side=tk.LEFT, padx=5)
        self.cookie_var = tk.StringVar()
        self.cookie_entry = ttk.Entry(
            self.cookie_frame, 
            textvariable=self.cookie_var, 
            font=("微软雅黑", 10)
        )
        self.cookie_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.chapter_frame = ttk.Frame(self.input_frame)
        self.chapter_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.chapter_frame, text="章节数量:", width=10).pack(side=tk.LEFT, padx=5)
        self.comic_num_var = tk.StringVar(value="1")
        self.comic_num_entry = ttk.Entry(
            self.chapter_frame, 
            textvariable=self.comic_num_var, 
            font=("微软雅黑", 10),
            width=10
        )
        self.comic_num_entry.pack(side=tk.LEFT, padx=5)
        
        self.download_path_frame = ttk.Frame(self.input_frame)
        self.download_path_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.download_path_frame, text="下载路径:", width=10).pack(side=tk.LEFT, padx=5)
        self.download_path_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads"))
        self.download_path_entry = ttk.Entry(
            self.download_path_frame, 
            textvariable=self.download_path_var, 
            font=("微软雅黑", 10)
        )
        self.download_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        def browse_download_path():
            path = filedialog.askdirectory(
                title="选择下载路径",
                initialdir=self.download_path_var.get()
            )
            if path:
                self.download_path_var.set(path)
        
        ttk.Button(
            self.download_path_frame, 
            text="浏览", 
            command=browse_download_path,
            width=8
        ).pack(side=tk.LEFT, padx=5)
        
        self.browser_frame = ttk.LabelFrame(self.input_frame, text="浏览器设置", padding="10")
        self.browser_frame.pack(fill=tk.X, pady=5)
        
        self.browser_type_frame = ttk.Frame(self.browser_frame)
        self.browser_type_frame.pack(fill=tk.X, pady=3)
        
        ttk.Label(self.browser_type_frame, text="浏览器类型:", width=10).pack(side=tk.LEFT, padx=5)
        self.browser_type_var = tk.StringVar(value="edge")
        browser_type_frame_inner = ttk.Frame(self.browser_type_frame)
        browser_type_frame_inner.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Radiobutton(
            browser_type_frame_inner, 
            text="Edge", 
            variable=self.browser_type_var, 
            value="edge"
        ).pack(side=tk.LEFT, padx=10)
        
        ttk.Radiobutton(
            browser_type_frame_inner, 
            text="Chrome", 
            variable=self.browser_type_var, 
            value="chrome"
        ).pack(side=tk.LEFT, padx=10)
        
        self.browser_path_frame = ttk.Frame(self.browser_frame)
        self.browser_path_frame.pack(fill=tk.X, pady=3)
        
        ttk.Label(self.browser_path_frame, text="浏览器路径:", width=10).pack(side=tk.LEFT, padx=5)
        self.browser_path_var = tk.StringVar(value=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
        self.browser_path_entry = ttk.Entry(
            self.browser_path_frame, 
            textvariable=self.browser_path_var, 
            font=("微软雅黑", 10)
        )
        self.browser_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        def on_browser_type_change(*args):
            browser_type = self.browser_type_var.get()
            if browser_type == "edge":
                default_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
            else:
                default_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            self.browser_path_var.set(default_path)
        
        self.browser_type_var.trace("w", on_browser_type_change)
        
        def browse_browser():
            path = filedialog.askopenfilename(
                title="选择浏览器可执行文件",
                filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
            )
            if path:
                self.browser_path_var.set(path)
        
        ttk.Button(
            self.browser_path_frame, 
            text="浏览", 
            command=browse_browser,
            width=8
        ).pack(side=tk.LEFT, padx=5)
        
        self.browser_mode_frame = ttk.Frame(self.browser_frame)
        self.browser_mode_frame.pack(fill=tk.X, pady=3)
        
        ttk.Label(self.browser_mode_frame, text="浏览器模式:", width=10).pack(side=tk.LEFT, padx=5)
        self.browser_mode_var = tk.StringVar(value="headed")
        browser_mode_frame_inner = ttk.Frame(self.browser_mode_frame)
        browser_mode_frame_inner.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Radiobutton(
            browser_mode_frame_inner, 
            text="有头模式", 
            variable=self.browser_mode_var, 
            value="headed"
        ).pack(side=tk.LEFT, padx=10)
        
        ttk.Radiobutton(
            browser_mode_frame_inner, 
            text="无头模式", 
            variable=self.browser_mode_var, 
            value="headless"
        ).pack(side=tk.LEFT, padx=10)
        
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, pady=10)
        
        self.confirm_button = ttk.Button(
            self.button_frame, 
            text="确定", 
            command=self.start_download,
            style="Accent.TButton"
        )
        self.confirm_button.pack(side=tk.RIGHT, padx=5)
        
        self.clear_button = ttk.Button(
            self.button_frame, 
            text="清空状态", 
            command=self.clear_status
        )
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        self.exit_button = ttk.Button(
            self.button_frame, 
            text="退出", 
            command=root.quit
        )
        self.exit_button.pack(side=tk.RIGHT, padx=5)
        
        self.progress_frame = ttk.LabelFrame(self.main_frame, text="下载进度", padding="10")
        self.progress_frame.pack(fill=tk.X, pady=5)
        
        self.info_frame = ttk.Frame(self.progress_frame)
        self.info_frame.pack(fill=tk.X, pady=5)
        
        self.progress_label = ttk.Label(
            self.info_frame,
            text="进度: 0/0 张图片",
            font=("微软雅黑", 10)
        )
        self.progress_label.pack(side=tk.LEFT, padx=5)
        
        self.speed_label = ttk.Label(
            self.info_frame,
            text="网速: 0 KB/s",
            font=("微软雅黑", 10)
        )
        self.speed_label.pack(side=tk.RIGHT, padx=5)
        
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            orient=tk.HORIZONTAL,
            mode='determinate',
            length=600
        )
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.status_frame = ttk.LabelFrame(self.main_frame, text="下载状态", padding="10")
        self.status_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.status_text = tk.Text(
            self.status_frame, 
            font=("微软雅黑", 10),
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.status_text.pack(fill=tk.BOTH, expand=True)
        
        self.scrollbar = ttk.Scrollbar(self.status_text, command=self.status_text.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.config(yscrollcommand=self.scrollbar.set)
        
        self.style = ttk.Style()
        self.style.configure(
            "Accent.TButton", 
            foreground="black", 
            background="black",
            font=("微软雅黑", 10, "bold")
        )
        self.style.map(
            "Accent.TButton",
            background=[("active", "gray")]
        )
    
    def parse_cookie_str(self, cookie_str, domain):
        """解析Cookie字符串"""
        cookies = []
        items = [item.strip() for item in cookie_str.split(';') if item.strip()]
        
        for item in items:
            if '=' in item:
                name, value = item.split('=', 1)
                name = name.strip()
                value = value.strip()
                
                try:
                    value = unquote(value)
                except:
                    pass
                
                cookies.append({
                    'name': name,
                    'value': value,
                    'domain': domain,
                    'path': '/'
                })
            else:
                cookies.append({
                    'name': item.strip(),
                    'value': '',
                    'domain': domain,
                    'path': '/'
                })
        
        return cookies
    
    def append_status(self, text):
        """向状态文本框添加内容"""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, text + "\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
        self.root.update()
    
    def clear_status(self):
        """清空状态文本框"""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state=tk.DISABLED)
    
    def reset_progress(self, total_images=0):
        """重置进度条"""
        self.total_images = total_images
        self.downloaded_images = 0
        self.total_downloaded_bytes = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.last_downloaded_bytes = 0
        
        self.progress_bar['value'] = 0
        self.progress_bar['maximum'] = total_images if total_images > 0 else 1
        self.progress_label.config(text=f"进度: 0/{total_images} 张图片")
        self.speed_label.config(text="网速: 0 KB/s")
    
    def update_progress(self, downloaded_bytes=0):
        """更新进度条和网速"""
        self.downloaded_images += 1
        self.total_downloaded_bytes += downloaded_bytes
        
        current_time = time.time()
        elapsed = current_time - self.last_update_time
        
        if elapsed >= 0.5:
            speed_bytes = self.total_downloaded_bytes - self.last_downloaded_bytes
            speed_kb = speed_bytes / elapsed / 1024
            self.last_update_time = current_time
            self.last_downloaded_bytes = self.total_downloaded_bytes
            
            if speed_kb >= 1024:
                speed_str = f"{speed_kb / 1024:.2f} MB/s"
            else:
                speed_str = f"{speed_kb:.2f} KB/s"
            self.speed_label.config(text=f"网速: {speed_str}")
        
        self.progress_bar['value'] = self.downloaded_images
        self.progress_label.config(text=f"进度: {self.downloaded_images}/{self.total_images} 张图片")
        self.root.update()
    
    def download_task(self):
        """下载任务函数"""
        try:
            site_name = self.site_var.get()
            if site_name == "快看":
                CONFIG = KUAICAN_CONFIG
            else:
                CONFIG = HAODUOMAN_CONFIG
            
            comic_name = self.comic_name_var.get().strip()
            if not comic_name:
                messagebox.showerror("错误", "请输入漫画名称")
                return
            
            comic_num_str = self.comic_num_var.get().strip()
            if not comic_num_str.isdigit() or int(comic_num_str) <= 0:
                messagebox.showerror("错误", "请输入有效的章节数量")
                return
            comic_num = int(comic_num_str)
            
            browser_path = self.browser_path_var.get().strip()
            if not browser_path or not os.path.exists(browser_path):
                messagebox.showerror("错误", "浏览器路径无效")
                return
            
            browser_mode = self.browser_mode_var.get()
            browser_type = self.browser_type_var.get()
            
            self.confirm_button.config(state=tk.DISABLED)
            
            self.append_status(f"正在初始化浏览器... (类型: {browser_type}, 模式: {browser_mode})")
            co = ChromiumOptions()
            co.set_browser_path(browser_path)
            
            # 设置随机端口避免冲突
            import random
            random_port = random.randint(9222, 9322)
            co.set_local_port(random_port)
            
            # 添加必要的启动参数
            co.set_argument("--remote-allow-origins=*")
            co.set_argument("--no-first-run")
            co.set_argument("--no-default-browser-check")
            co.set_argument("--disable-blink-features=AutomationControlled")
            
            if browser_mode == "headless":
                co.headless()
                co.set_argument("--disable-gpu")
                co.set_argument("--no-sandbox")
                co.set_argument("--disable-dev-shm-usage")
                self.append_status("已启用无头模式")
            
            self.append_status(f"尝试连接浏览器端口: {random_port}")
            try:
                tab = ChromiumPage(co)
            except Exception as e:
                self.append_status(f"浏览器连接失败: {str(e)}")
                self.append_status("尝试使用默认配置...")
                co = ChromiumOptions()
                co.set_browser_path(browser_path)
                co.set_argument("--remote-allow-origins=*")
                tab = ChromiumPage(co)
            cookie = self.cookie_var.get().strip()
            
            try:
                self.append_status(f"访问网站: {CONFIG['COMIC_SITE_URL']}")
                tab.get(CONFIG['COMIC_SITE_URL'])
                
                if cookie:
                    self.append_status("正在设置Cookie...")
                    try:
                        domain = urlparse(CONFIG['COMIC_SITE_URL']).netloc
                        cookies = self.parse_cookie_str(cookie, domain)
                        self.append_status(f"解析到 {len(cookies)} 个Cookie项")
                        tab.set.cookies(cookies)
                        self.append_status("Cookie已设置")
                        self.append_status("刷新页面应用Cookie...")
                        tab.refresh()
                        self.append_status("Cookie已应用")
                        
                        self.append_status(f"正在搜索漫画: {comic_name}")
                        tab.ele(f"xpath:{CONFIG['XPATHS']['search_input']}").input(comic_name)
                        tab.ele(f"xpath:{CONFIG['XPATHS']['search_button']}").click()
                        time.sleep(0.5)
                        target_comic_list = tab.ele(f"xpath:{CONFIG['XPATHS']['search_result']}")
                        
                        if site_name == "快看":
                            target_comic_tab = target_comic_list.click.for_new_tab()
                        else:
                            href = target_comic_list.attr('href')
                            target_comic_tab = tab.new_tab(href)
                        
                        self.append_status("成功打开漫画详情页")
                    except Exception as e:
                        self.append_status(f"设置Cookie失败: {str(e)}")
                        self.append_status(f"正在搜索漫画: {comic_name}")
                        tab.ele(f"xpath:{CONFIG['XPATHS']['search_input']}").input(comic_name)
                        tab.ele(f"xpath:{CONFIG['XPATHS']['search_button']}").click()
                        time.sleep(0.5)
                        target_comic_list = tab.ele(f"xpath:{CONFIG['XPATHS']['search_result']}")
                        
                        if site_name == "快看":
                            target_comic_tab = target_comic_list.click.for_new_tab()
                        else:
                            href = target_comic_list.attr('href')
                            target_comic_tab = tab.new_tab(href)
                        
                        self.append_status("成功打开漫画详情页")
                else:
                    self.append_status("未提供Cookie，跳过设置")
                    self.append_status(f"正在搜索漫画: {comic_name}")
                    tab.ele(f"xpath:{CONFIG['XPATHS']['search_input']}").input(comic_name)
                    tab.ele(f"xpath:{CONFIG['XPATHS']['search_button']}").click()
                    time.sleep(0.5)
                    target_comic_list = tab.ele(f"xpath:{CONFIG['XPATHS']['search_result']}")
                    
                    if site_name == "快看":
                        target_comic_tab = target_comic_list.click.for_new_tab()
                    else:
                        href = target_comic_list.attr('href')
                        target_comic_tab = tab.new_tab(href)
                    
                    self.append_status("成功打开漫画详情页")
                
                self.append_status("Cookie已准备就绪")
                
                try:
                    coverimg_xpath = "xpath:" + CONFIG['XPATHS']['cover_image']
                    coverimg_url = target_comic_tab.ele(coverimg_xpath).attr("src")
                    self.append_status(f"封面图片URL: {coverimg_url}")
                except Exception as e:
                    self.append_status(f"获取封面图片失败: {e}")
                    coverimg_url = None
                
                self.append_status(f"正在收集第1-{comic_num}章的图片链接...")
                
                if site_name == "快看":
                    all_chapters_data = kuaikan_collect_chapters_images(target_comic_tab, comic_num)
                else:
                    all_chapters_data = haoduoman_collect_chapters_images(target_comic_tab, comic_num, tab)
                
                if all_chapters_data:
                    self.append_status(f"成功收集到 {len(all_chapters_data)} 个章节的图片链接")
                    
                    total_images = 0
                    for chapter_data in all_chapters_data:
                        total_images += len(chapter_data.get('herf_list', []))
                    self.reset_progress(total_images)
                    self.append_status(f"总计 {total_images} 张图片待下载")
                else:
                    self.append_status("没有获取到任何章节的图片链接")
                    self.reset_progress(0)
                
                download_path = self.download_path_var.get().strip()
                
                if coverimg_url:
                    self.append_status(f"正在下载封面图片...")
                    asyncio.run(download_cover_image(coverimg_url, comic_name, download_path if download_path else None))
                    self.append_status("封面图片下载完成")
                
                if all_chapters_data:
                    self.append_status("正在下载章节图片...")
                    asyncio.run(download_all_chapters(all_chapters_data, comic_name, download_path if download_path else None, self.update_progress))
                    self.append_status("章节图片下载完成")
                
                self.append_status("正在获取图片尺寸...")
                base_path = download_path if download_path else os.getcwd()
                main_folder = os.path.join(base_path, comic_name)
                get_image_dimensions(main_folder)
                self.append_status("图片尺寸获取完成")
                
                self.append_status("正在压缩文件夹...")
                zip_main_folder(comic_name, download_path if download_path else None)
                self.append_status("文件夹压缩完成")
                
                messagebox.showinfo("成功", f"漫画 {comic_name} 下载完成！")
                
            finally:
                tab.close()
                self.append_status("浏览器已关闭")
                
        except Exception as e:
            self.append_status(f"下载过程中出错: {e}")
            import traceback
            self.append_status(traceback.format_exc())
            messagebox.showerror("错误", f"下载过程中出错: {e}")
        finally:
            self.confirm_button.config(state=tk.NORMAL)
    
    def start_download(self):
        """开始下载"""
        download_thread = threading.Thread(target=self.download_task)
        download_thread.daemon = True
        download_thread.start()


def main():
    """主函数"""
    root = tk.Tk()
    app = ComicDownloaderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
