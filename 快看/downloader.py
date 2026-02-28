# 下载模块
# 实现异步下载图片、下载封面等功能
import os
import asyncio
import aiohttp
from config import CONCURRENT_DOWNLOAD_LIMIT, DOWNLOAD_DELAY


async def async_download_image(session, url, i, folder_name):
    """异步下载单张图片"""


    try:
        # 发送GET请求获取图片
        async with session.get(url,ssl=False) as response:
            if response.status == 200:
                # 保存图片，文件名为序号
                file_path = os.path.join(folder_name, f"{i}.jpg")
                content = await response.read()
                with open(file_path, 'wb') as f:
                    f.write(content)
                print(f"下载成功: {file_path}")
            else:
                print(f"下载失败 (状态码: {response.status}): {url}")
    except Exception as e:
        print(f"下载第{i}张图片时出错: {e}")


async def async_download_images(herf_list, folder_name):
    """异步方式下载图片到指定文件夹，文件名按序号命名"""
    # 创建文件夹
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        print(f"创建文件夹: {folder_name}")

    print(f"\n开始下载图片到 {folder_name} (异步方式)...")
    start_time = time.time()

    # 创建异步会话，禁用SSL验证
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        # 创建任务列表
        tasks = []
        for i, url in enumerate(herf_list, 1):
            task = async_download_image(session, url, i, folder_name)
            tasks.append(task)
            # 限制并发数
            if len(tasks) >= CONCURRENT_DOWNLOAD_LIMIT:
                await asyncio.gather(*tasks)
                tasks = []
                # 每批任务之间添加小延迟
                await asyncio.sleep(DOWNLOAD_DELAY)
        
        # 处理剩余任务
        if tasks:
            await asyncio.gather(*tasks)

    end_time = time.time()
    print(f"\n图片下载完成，耗时: {end_time - start_time} 秒")


async def download_cover_image(cover_url, main_folder, download_path=None):
    """下载封面图片到指定文件夹"""
    # 如果指定了下载路径，则使用指定路径，否则使用main_folder
    if download_path:
        main_folder = os.path.join(download_path, main_folder)
    
    # 创建封面文件夹
    cover_folder = os.path.join(main_folder, "0")
    if not os.path.exists(cover_folder):
        os.makedirs(cover_folder)
        print(f"创建封面文件夹: {cover_folder}")
    
    print(f"\n开始下载封面图片...")
    start_time = time.time()
    
    # 请求头，模拟浏览器请求
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "cache-control": "max-age=0",
        "referer": "https://cn.bing.com/",
        "sec-ch-ua": "\"Not:A-Brand\";v=\"99\", \"Microsoft Edge\";v=\"145\", \"Chromium\";v=\"145\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0"
    }
    
    try:
        # 发送GET请求获取封面图片
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(cover_url, headers=headers) as response:
                if response.status == 200:
                    file_path = os.path.join(cover_folder, "cover.jpg")
                    content = await response.read()
                    with open(file_path, 'wb') as f:
                        f.write(content)
                    print(f"封面下载成功: {file_path}")
                else:
                    print(f"封面下载失败 (状态码: {response.status})")
    except Exception as e:
        print(f"下载封面时出错: {e}")
    
    end_time = time.time()
    print(f"封面下载耗时: {end_time - start_time:.2f} 秒")


async def download_all_chapters(chapters_data, comic_name, download_path=None):
    """协程下载所有章节的图片"""
    print("\n开始协程下载所有章节图片...")
    start_time = time.time()
    
    # 如果指定了下载路径，则使用指定路径，否则使用comic_name作为主文件夹
    if download_path:
        main_folder = os.path.join(download_path, comic_name)
    else:
        main_folder = comic_name
    
    if not os.path.exists(main_folder):
        os.makedirs(main_folder)
        print(f"创建漫画主文件夹: {main_folder}")
    
    # 创建下载任务
    tasks = []
    for chapter_data in chapters_data:
        chapter_num = chapter_data['chapter_num']
        herf_list = chapter_data['herf_list']
        
        if herf_list:
            # 创建章节文件夹
            folder_name = os.path.join(main_folder, str(chapter_num))
            task = async_download_images(herf_list, folder_name)
            tasks.append(task)
        else:
            print(f"章节{chapter_num}没有获取到图片链接，跳过下载")
    
    # 执行所有下载任务
    if tasks:
        await asyncio.gather(*tasks)
    
    end_time = time.time()
    print(f"\n所有章节图片下载完成，总耗时: {end_time - start_time} 秒")
    
    # 导入utils模块获取图片尺寸
    from utils import get_image_dimensions
    get_image_dimensions(main_folder, comic_name)


# 导入必要的模块
import time
