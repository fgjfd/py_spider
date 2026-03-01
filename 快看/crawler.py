# 爬虫模块
# 实现获取图片链接、多线程收集章节等功能 - 快看优化版
import time
import threading

from config import MAX_RETRIES, MAX_RETRY, WAIT_TIME, MAX_THREADS, XPATHS
from utils import is_normal_url


def get_chapter_image_urls(chapter_tab, max_img_num):
    """获取单个章节的图片URL列表 - 直接获取data-src"""
    herf_list = []
    
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


def collect_chapter_images(chapter_info):
    """收集单个章节的图片URL"""
    chapter_num = chapter_info['chapter_num']
    chapter_tab = chapter_info['tab']
    
    print(f"正在处理章节{chapter_num}")
    
    try:
        time.sleep(WAIT_TIME * 2)
        
        img_elements = chapter_tab.eles("xpath:" + XPATHS['chapter_image_parent'])
        max_img_num = len(img_elements)
        print(f"章节{chapter_num}检测到{max_img_num}张图片")
        
        herf_list = get_chapter_image_urls(chapter_tab, max_img_num)
        
    except Exception as e:
        print(f"处理章节{chapter_num}时出错: {e}")
        herf_list = []
    
    chapter_tab.close()
    
    return {
        'chapter_num': chapter_num,
        'herf_list': herf_list
    }


def click_chapter_group(target_comic_tab, group_index):
    """点击章节组按钮"""
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


def collect_chapters_images(target_comic_tab, comic_num, max_threads=MAX_THREADS):
    """多线程收集所有章节的图片URL"""
    print(f"设置最大同时收集线程数: {max_threads}")

    chapter_list_xpath = XPATHS['chapter_list']
    chapter_eles = target_comic_tab.eles("xpath:" + chapter_list_xpath)
    all_chapters_num = len(chapter_eles)
    print(f"总章节数: {all_chapters_num}")

    actual_comic_num = min(comic_num, all_chapters_num)
    print(f"用户请求下载 {comic_num} 章，实际可下载 {actual_comic_num} 章")

    all_chapters_data = []
    current_chapter = 1

    while current_chapter <= actual_comic_num:
        group_index = (current_chapter - 1) // 50 + 1
        click_chapter_group(target_comic_tab, group_index)
        
        chapter_eles = target_comic_tab.eles("xpath:" + chapter_list_xpath)
        chapters_in_group = len(chapter_eles)
        
        group_end = min(current_chapter + max_threads - 1, actual_comic_num)
        group_end = min(group_end, current_chapter + chapters_in_group - 1)
        
        print(f"\n处理章节范围: {current_chapter}-{group_end}")

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
