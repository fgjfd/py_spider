from hashlib import new

from DrissionPage import ChromiumOptions, ChromiumPage
import time
import os
import requests
import asyncio
import aiohttp
import threading


def is_normal_url(url):
    """检查URL是否有效"""
    return url and ('http' in url or 'https' in url)


def get_pic_herf(pic_tab, pic_des, wait_time, max_num, max_retries=3):
    """获取单个章节的图片URL列表"""
    herf_list = []

    print("开始爬取")
    start_time = time.time()

    # 逐个处理元素
    for num in range(1, max_num + 1):
        current_pic_des = pic_des.replace("num", str(num))
        herf = None
        retry_count = 0

        while retry_count < max_retries:
            try:
                # 尝试获取元素
                img_ele = pic_tab.ele(f"xpath:{current_pic_des}", timeout=3)

                # 滚动到元素使其可见
                pic_tab.scroll.to_see(img_ele)

                # 等待加载
                time.sleep(wait_time)

                # 获取链接
                herf = img_ele.attr("src")

                if is_normal_url(herf):
                    print(f"第{num}张图片(正常): {herf}")
                    herf_list.append(herf)
                    break
                else:
                    print(f"第{num}张图片(非正常): {herf} (尝试 {retry_count + 1}/{max_retries})")
                    retry_count += 1
                    # 等待一段时间后重试
                    time.sleep(0.5)

            except Exception as e:
                print(f"获取第{num}张图片时出错(尝试 {retry_count + 1}/{max_retries}): {e}")
                retry_count += 1
                time.sleep(0.5)

        if not herf or not is_normal_url(herf):
            print(f"第{num}张图片: 经过{max_retries}次尝试仍未获取到有效URL")

    end_time = time.time()
    print("\nover")
    print(f"耗时: {end_time - start_time} 秒")
    print(f"共获取{len(herf_list)}张图片")

    # 打印保存的链接
    print("\n保存的链接:")
    for i, herf in enumerate(herf_list, 1):
        print(f"{i}: {herf}")

    return herf_list



def search_comic(tab, comic_name):
    """搜索漫画并返回详情页标签页"""
    tab.get("https://www.kuaikanmanhua.com/")
    tab.ele("xpath:/html/body/div[1]/div/div/div/div[1]/div[2]/div/div[1]/input").input(comic_name)
    tab.ele("xpath:/html/body/div[1]/div/div/div/div[1]/div[2]/div/div[1]/a").click()
    target_comic_list = tab.ele("xpath:/html/body/div[1]/div/div/div/div[3]/div[1]/div[1]/div[1]/a/div[1]/img[1]")
    target_comic = target_comic_list.click.for_new_tab()
    
    return target_comic  # 返回漫画详情页标签页


def basic_info():
    """获取用户输入的漫画名称和章节数"""
    comic_name = input("你想看什么漫画").strip().replace("' ", "").replace("\" ", "")
    comic_num = input("你想看第几张漫画").strip()
    return comic_name, int(comic_num)


def collect_chapter_images(chapter_info):
    """收集单个章节的图片URL"""
    chapter_num = chapter_info['chapter_num']
    chapter_tab = chapter_info['tab']
    max_img_num = chapter_info['max_img_num']
    
    # 使用XPath获取图片
    pic_des = "/html/body/div[1]/div/div/div/div[4]/div[1]/div[1]/div[num]/img[1]"
    
    # 获取图片链接
    herf_list = get_pic_herf(chapter_tab, pic_des, wait_time=0.1, max_num=max_img_num, max_retries=5)
    
    # 关闭标签页
    chapter_tab.close()
    
    return {
        'chapter_num': chapter_num,
        'herf_list': herf_list
    }


def collect_chapters_images(target_comic_tab, comic_num, max_threads=3):
    """多线程收集所有章节的图片URL"""
    print(f"设置最大同时收集线程数: {max_threads}")

    # 存储所有章节的图片数据
    all_chapters_data = []

    # 获取章节信息（只收集信息，不打开页面）
    chapter_xpaths = []
    for num in range(1, comic_num + 1):
        chapter_xpath = f"/html/body/div[1]/div/div/div/div[2]/div/div[2]/div[1]/div[1]/div/div[3]/div[{num}]"
        chapter_xpaths.append((num, chapter_xpath))
    
    # 批量处理章节
    for i in range(0, len(chapter_xpaths), max_threads):
        # 获取当前批次的章节
        batch = chapter_xpaths[i:i + max_threads]
        print(f"\n处理批次 {i//max_threads + 1}: 章节 {[chap[0] for chap in batch]}")
        
        # 打开当前批次的章节页面
        batch_chapters_info = []
        for num, xpath in batch:
            try:
                chapter_ele = target_comic_tab.ele(f"xpath:{xpath}")
                chapter_tab = chapter_ele.click.for_new_tab()
                
                # 获取章节中的图片数量
                img_elements = chapter_tab.eles("xpath:/html/body/div/div/div/div/div[4]/div[1]/div[1]/div/img[1]")
                max_img_num = len(img_elements)
                
                # 存储章节信息
                batch_chapters_info.append({
                    'chapter_num': num,
                    'tab': chapter_tab,
                    'max_img_num': max_img_num
                })
                
                print(f"打开第{num}章节，检测到{max_img_num}张图片")
                
            except Exception as e:
                print(f"打开第{num}章节时出错: {e}")
        
        # 使用多线程收集当前批次章节的图片URL
        threads = []
        results = []
        
        # 创建一个线程结果收集函数
        def thread_wrapper(chapter_info):
            result = collect_chapter_images(chapter_info)
            results.append(result)
        
        for chapter_info in batch_chapters_info:
            thread = threading.Thread(target=thread_wrapper, args=(chapter_info,))
            threads.append(thread)
            thread.start()
        
        # 等待当前批次的线程完成
        for thread in threads:
            thread.join()
        
        # 将当前批次的结果添加到总结果中
        all_chapters_data.extend(results)
    
    return all_chapters_data


async def async_download_image(session, url, i, folder_name):
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "cache-control": "max-age=0",
        "cookie": "resolution=1080 * 1920; TDC_itoken=702744311%3A1768998886; referer_name=bing; sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%2219be4b873ff297-004f4f92ff82246-4c657b58-1327104-19be4b874001991%22%2C%22first_id%22%3A%22%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E8%87%AA%E7%84%B6%E6%90%9C%E7%B4%A2%E6%B5%81%E9%87%8F%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC%22%2C%22%24latest_referrer%22%3A%22https%3A%2F%2Fcn.bing.com%2F%22%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMTliZTA4Yzk5OTY2Y2YtMGY1MTljNjhjOWI1YjItNGM2NTdiNTgtMTMyNzEwNC0xOWJlMDhjOTk5NzE5MzQifQ%3D%3D%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%22%2C%22value%22%3A%22%22%7D%2C%22%24device_id%22%3A%2219be08c99966cf-0f519c68c9b5b2-4c657b58-1327104-19be08c99971934%22%7D; kk_s_t=1771337828142; Hm_lvt_c826b0776d05b85d834c5936296dc1d5=1769601627,1771311159,1771330584,1771337828; Hm_lpvt_c826b0776d05b85d834c5936296dc1d5=1771337828; HMACCOUNT=41C4669A85191AC1",
        "if-none-match": "\"38990-p5GSCbeZHMMxjfR4PxrqN6vaR50\"",
        "priority": "u=0, i",
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

    """异步下载单张图片"""
    try:
        async with session.get(url, headers=headers, ssl=False) as response:
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
            # 限制并发数，每10个任务一批
            if len(tasks) >= 10:
                await asyncio.gather(*tasks)
                tasks = []
                # 每批任务之间添加小延迟
                await asyncio.sleep(0.2)
        
        # 处理剩余任务
        if tasks:
            await asyncio.gather(*tasks)

    end_time = time.time()
    print(f"\n图片下载完成，耗时: {end_time - start_time} 秒")


async def download_all_chapters(chapters_data):
    """协程下载所有章节的图片"""
    print("\n开始协程下载所有章节图片...")
    start_time = time.time()
    
    # 为每个章节创建下载任务
    tasks = []
    for chapter_data in chapters_data:
        chapter_num = chapter_data['chapter_num']
        herf_list = chapter_data['herf_list']
        
        if herf_list:
            folder_name = str(chapter_num)
            task = async_download_images(herf_list, folder_name)
            tasks.append(task)
        else:
            print(f"章节{chapter_num}没有获取到图片链接，跳过下载")
    
    # 等待所有下载任务完成
    if tasks:
        await asyncio.gather(*tasks)
    
    end_time = time.time()
    print(f"\n所有章节图片下载完成，总耗时: {end_time - start_time} 秒")



def main():
    """主函数"""
    co = ChromiumOptions().set_paths(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    
    comic_name, comic_num = basic_info()
    tab = ChromiumPage(co)
    
    target_comic_tab = search_comic(tab, comic_name)
    
    # 多线程收集所有章节的图片URL
    all_chapters_data = collect_chapters_images(target_comic_tab, comic_num, max_threads=3)

    # 协程下载所有章节的图片
    if all_chapters_data:
        asyncio.run(download_all_chapters(all_chapters_data))
    else:
        print("没有获取到任何章节的图片链接，跳过下载")

    # 关闭主标签页
    tab.close()

    input("按回车键结束程序...")


if __name__ == "__main__":
    main()
