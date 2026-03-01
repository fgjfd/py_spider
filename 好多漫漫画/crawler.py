# 爬虫模块
# 实现获取图片链接、多线程收集章节等功能 - 好多漫巧办法
import time
import threading
import re

from config import WAIT_TIME, MAX_THREADS, XPATHS
from utils import is_normal_url


def get_chapter_image_urls(chapter_tab, max_img_num):
    """获取单个章节的图片URL列表 - 巧办法，直接获取data-original"""
    herf_list = []
    
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


def collect_chapter_images(chapter_info):
    """收集单个章节的图片URL"""
    chapter_num = chapter_info['chapter_num']
    chapter_url = chapter_info['url']
    main_tab = chapter_info['main_tab']
    
    print(f"正在处理章节{chapter_num}: {chapter_url}")
    
    try:
        chapter_tab = main_tab.new_tab(chapter_url)
        time.sleep(WAIT_TIME * 2)
        
        img_elements = chapter_tab.eles("xpath:" + XPATHS['chapter_image_parent'])
        max_img_num = len(img_elements)
        print(f"章节{chapter_num}检测到{max_img_num}张图片")
        
        herf_list = get_chapter_image_urls(chapter_tab, max_img_num)
        
        chapter_tab.close()
        
    except Exception as e:
        print(f"处理章节{chapter_num}时出错: {e}")
        herf_list = []
    
    return {
        'chapter_num': chapter_num,
        'herf_list': herf_list
    }


def collect_chapters_images(target_comic_tab, comic_num, main_tab, max_threads=MAX_THREADS):
    """多线程收集所有章节的图片URL - 巧办法拼凑URL"""
    print(f"设置最大同时收集线程数: {max_threads}")
    
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
        group_end = min(current_chapter + max_threads - 1, actual_comic_num)
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
            result = collect_chapter_images(chapter_info)
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
