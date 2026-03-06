# 爬虫模块 - 完全照抄各站点原有逻辑
import time
import threading
import re
import concurrent.futures

from config import SITES
from utils import is_normal_url


class ComicCrawler:
    """通用漫画爬虫类"""
    
    def __init__(self, site_name, browser_path, headless=False, cookie_str=None):
        from DrissionPage import ChromiumOptions, ChromiumPage
        from urllib.parse import urlparse, unquote
        
        self.site_name = site_name
        self.site_config = SITES[site_name]
        self.xpaths = self.site_config['xpaths']
        self.image_attr = self.site_config['image_attr']
        self.cookie_str = cookie_str
        
        print(f"正在初始化浏览器...")
        co = ChromiumOptions().set_paths(browser_path)
        
        # 设置新的调试端口，避免冲突
        import random
        debug_port = random.randint(9223, 9322)
        co.set_argument(f"--remote-debugging-port={debug_port}")
        
        if headless:
            co.headless()
            co.set_argument("--disable-gpu")
            co.set_argument("--no-sandbox")
            co.set_argument("--disable-dev-shm-usage")
            print("已启用无头模式")
        else:
            print("已启用有头模式")
        
        try:
            self.page = ChromiumPage(co)
            self.tab = self.page
        except Exception as e:
            print(f"浏览器连接失败: {e}")
            print("尝试关闭现有浏览器进程并重新启动...")
            import os
            import subprocess
            # 尝试关闭占用9222端口的进程
            try:
                subprocess.run(['taskkill', '/F', '/IM', 'msedge.exe'], capture_output=True)
                subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], capture_output=True)
                time.sleep(2)
            except:
                pass
            # 重新尝试
            self.page = ChromiumPage(co)
            self.tab = self.page
    
    def parse_cookie_str(self, cookie_str, domain):
        """解析Cookie字符串为DrissionPage可用的格式"""
        from urllib.parse import unquote
        
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
    
    def set_cookie(self):
        """设置Cookie"""
        if not self.cookie_str:
            return False
        
        try:
            from urllib.parse import urlparse
            
            print("正在设置Cookie...")
            domain = urlparse(self.site_config['site_url']).netloc
            
            cookies = self.parse_cookie_str(self.cookie_str, domain)
            print(f"解析到 {len(cookies)} 个Cookie项")
            
            self.tab.set.cookies(cookies)
            print("Cookie已设置")
            
            self.tab.refresh()
            print("Cookie已应用")
            return True
        except Exception as e:
            print(f"设置Cookie失败: {e}")
            return False
    
    def search_comic(self, comic_name):
        """搜索漫画 - 根据站点使用不同逻辑"""
        if self.site_name == '快看':
            return self.search_comic_kuaikan(comic_name)
        elif self.site_name == '好多漫':
            return self.search_comic_haoduoman(comic_name)
        elif self.site_name == '御漫画':
            return self.search_comic_yumanhua(comic_name)
    
    def search_comic_kuaikan(self, comic_name):
        """快看搜索逻辑 - 完全照抄快看文件夹"""
        self.tab.get(self.site_config['site_url'])
        
        if self.cookie_str:
            self.set_cookie()
        
        self.tab.ele(f"xpath:{self.xpaths['search_input']}").input(comic_name)
        self.tab.ele(f"xpath:{self.xpaths['search_button']}").click()
        
        time.sleep(0.5)
        
        target_comic_list = self.tab.ele(f"xpath:{self.xpaths['search_result']}")
        target_comic_tab = target_comic_list.click.for_new_tab()
        
        return target_comic_tab
    
    def search_comic_haoduoman(self, comic_name):
        """好多漫搜索逻辑 - 完全照抄好多漫文件夹"""
        self.tab.get(self.site_config['site_url'])
        
        self.tab.ele(f"xpath:{self.xpaths['search_input']}").input(comic_name)
        self.tab.ele(f"xpath:{self.xpaths['search_button']}").click()
        
        time.sleep(0.5)
        
        target_comic_list = self.tab.ele(f"xpath:{self.xpaths['search_result']}")
        href = target_comic_list.attr('href')
        target_comic_tab = self.tab.new_tab(href)
        
        return target_comic_tab
    
    def search_comic_yumanhua(self, comic_name):
        """御漫画搜索逻辑 - 完全照抄御漫画文件夹"""
        self.tab.get(self.site_config['site_url'])
        
        print(f"正在搜索漫画: {comic_name}")
        
        search_button = self.tab.ele(f"xpath:{self.xpaths['search_button']}")
        search_button.click()
        time.sleep(0.5)
        
        search_input = self.tab.ele(f"xpath:{self.xpaths['search_input']}")
        search_input.input(comic_name)
        time.sleep(0.3)
        
        search_submit = self.tab.ele(f"xpath:{self.xpaths['search_submit']}")
        search_submit.click()
        time.sleep(1)
        
        result = self.tab.ele(f"xpath:{self.xpaths['search_result']}")
        result.click()
        time.sleep(1)
        
        print("已打开漫画详情页")
        return self.tab
    
    def get_cover_image(self, target_comic_tab):
        """获取封面图片"""
        try:
            coverimg_xpath = "xpath:" + self.xpaths['cover_image']
            coverimg_url = target_comic_tab.ele(coverimg_xpath).attr("src")
            print(f"封面图片URL: {coverimg_url}")
            return coverimg_url
        except Exception as e:
            print(f"获取封面图片失败: {e}")
            return None
    
    def get_chapter_count(self, target_comic_tab):
        """获取章节数量"""
        if self.site_name == '快看':
            chapter_list_xpath = self.xpaths['chapter_list']
            chapter_eles = target_comic_tab.eles("xpath:" + chapter_list_xpath)
            return len(chapter_eles)
        elif self.site_name == '好多漫':
            chapter_list_xpath = self.xpaths['chapter_list']
            chapter_eles = target_comic_tab.eles("xpath:" + chapter_list_xpath)
            return len(chapter_eles)
        elif self.site_name == '御漫画':
            # 先点击"显示更多"按钮展开所有章节
            click_show_more_yumanhua(self, target_comic_tab)
            chapter_elements = target_comic_tab.eles(f"xpath:{self.xpaths['chapter_list']}")
            return len(chapter_elements)
        return 0
    
    def collect_chapters_images(self, target_comic_tab, chapter_start=1, chapter_end=0, max_workers=10, progress_callback=None):
        """收集章节图片 - 根据站点使用不同逻辑
        
        Args:
            chapter_start: 起始章节号（从1开始）
            chapter_end: 结束章节号（0表示到最后一章）
        """
        if self.site_name == '快看':
            return collect_chapters_images_kuaikan(self, target_comic_tab, chapter_start, chapter_end, progress_callback)
        elif self.site_name == '好多漫':
            return collect_chapters_images_haoduoman(self, target_comic_tab, chapter_start, chapter_end, progress_callback)
        elif self.site_name == '御漫画':
            return collect_chapters_images_yumanhua(self, target_comic_tab, chapter_start, chapter_end, max_workers, progress_callback)


# ========== 快看完整逻辑 - 完全照抄 ==========

def get_chapter_image_urls_kuaikan(chapter_tab, max_img_num, xpaths, image_attr):
    """快看获取单个章节图片URL - 完全照抄"""
    herf_list = []
    
    print("开始获取图片URL...")
    
    for num in range(1, max_img_num + 1):
        try:
            img_xpath = xpaths['chapter_image'].replace("num", str(num))
            img_ele = chapter_tab.ele(f"xpath:{img_xpath}", timeout=3)
            herf = img_ele.attr(image_attr)
            
            if is_normal_url(herf):
                print(f"第{num}张图片: {herf}")
                herf_list.append(herf)
            else:
                print(f"第{num}张图片URL无效: {herf}")
                
        except Exception as e:
            print(f"获取第{num}张图片时出错: {e}")
    
    return herf_list


def collect_chapter_images_kuaikan(chapter_info, xpaths, image_attr, max_wait_time=3):
    """快看收集单个章节
    
    Args:
        max_wait_time: 最大等待时间（秒），如果超过此时间未获取到图片则重新加载页面
    """
    chapter_num = chapter_info['chapter_num']
    chapter_tab = chapter_info['tab']
    
    print(f"正在处理章节{chapter_num}")
    
    try:
        time.sleep(1)
        
        # 检查是否在max_wait_time秒内获取到图片
        start_time = time.time()
        retry_count = 0
        max_retries = 3
        max_img_num = 0
        
        while retry_count <= max_retries:
            img_elements = chapter_tab.eles("xpath:" + xpaths['chapter_image_parent'])
            max_img_num = len(img_elements)
            
            if max_img_num > 0:
                print(f"章节{chapter_num}检测到{max_img_num}张图片")
                break
            
            elapsed = time.time() - start_time
            if elapsed >= max_wait_time:
                if retry_count < max_retries:
                    retry_count += 1
                    print(f"章节{chapter_num} ⚠️ {max_wait_time}秒内未检测到图片，第{retry_count}次重新加载页面...")
                    chapter_tab.refresh()
                    time.sleep(1)
                    start_time = time.time()
                else:
                    print(f"章节{chapter_num} ✗ 已达到最大重试次数({max_retries})，仍未检测到图片")
                    chapter_tab.close()
                    return {
                        'chapter_num': chapter_num,
                        'herf_list': []
                    }
            else:
                time.sleep(0.5)
        
        herf_list = get_chapter_image_urls_kuaikan(chapter_tab, max_img_num, xpaths, image_attr)
        
    except Exception as e:
        print(f"处理章节{chapter_num}时出错: {e}")
        herf_list = []
    
    chapter_tab.close()
    
    return {
        'chapter_num': chapter_num,
        'herf_list': herf_list
    }


def click_chapter_group_kuaikan(target_comic_tab, group_index, xpaths):
    """快看点击章节组 - 完全照抄"""
    try:
        group_button_xpath = f"{xpaths['chapter_group_button']}[{group_index}]"
        group_button = target_comic_tab.ele(f"xpath:{group_button_xpath}")
        group_button.click()
        time.sleep(0.5)
        print(f"点击第{group_index}组按钮")
        return True
    except Exception as e:
        print(f"点击第{group_index}组按钮失败: {e}")
        return False


def collect_chapters_images_kuaikan(self, target_comic_tab, chapter_start=1, chapter_end=0, max_threads=3, progress_callback=None):
    """快看完整章节收集逻辑 - 完全照抄"""
    print(f"设置最大同时收集线程数: {max_threads}")

    chapter_list_xpath = self.xpaths['chapter_list']
    chapter_eles = target_comic_tab.eles("xpath:" + chapter_list_xpath)
    all_chapters_num = len(chapter_eles)
    print(f"总章节数: {all_chapters_num}")
    
    # 计算实际下载范围
    actual_start = max(chapter_start, 1)
    actual_end = min(chapter_end, all_chapters_num) if chapter_end > 0 else all_chapters_num
    
    if actual_start > all_chapters_num:
        print(f"起始章节 {actual_start} 超过总章节数 {all_chapters_num}")
        return []
    
    actual_comic_num = actual_end
    print(f"将下载第 {actual_start}-{actual_end} 章，共 {actual_end - actual_start + 1} 章")

    all_chapters_data = []
    current_chapter = actual_start

    while current_chapter <= actual_comic_num:
        group_index = (current_chapter - 1) // 50 + 1
        click_chapter_group_kuaikan(target_comic_tab, group_index, self.xpaths)
        
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
            result = collect_chapter_images_kuaikan(chapter_info, self.xpaths, self.image_attr)
            results.append(result)

        for chapter_info in batch_chapters_info:
            thread = threading.Thread(target=thread_wrapper, args=(chapter_info,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        all_chapters_data.extend(results)
        for _ in results:
            if progress_callback:
                progress_callback()
        current_chapter = group_end + 1

    return all_chapters_data


# ========== 好多漫完整逻辑 - 完全照抄 ==========

def get_chapter_image_urls_haoduoman(chapter_tab, max_img_num, xpaths, image_attr):
    """好多漫获取单个章节图片URL - 完全照抄"""
    herf_list = []
    
    for num in range(1, max_img_num + 1):
        try:
            div_xpath = xpaths['chapter_image_data_original'].replace("num", str(num))
            div_ele = chapter_tab.ele(f"xpath:{div_xpath}", timeout=3)
            herf = div_ele.attr(image_attr)
            
            if is_normal_url(herf):
                print(f"第{num}张图片: {herf}")
                herf_list.append(herf)
            else:
                print(f"第{num}张图片URL无效: {herf}")
                
        except Exception as e:
            print(f"获取第{num}张图片时出错: {e}")
    
    return herf_list


def collect_chapter_images_haoduoman(chapter_info, xpaths, image_attr, max_wait_time=3):
    """好多漫收集单个章节
    
    Args:
        max_wait_time: 最大等待时间（秒），如果超过此时间未获取到图片则重新加载页面
    """
    chapter_num = chapter_info['chapter_num']
    chapter_url = chapter_info['url']
    main_tab = chapter_info['main_tab']
    
    print(f"正在处理章节{chapter_num}: {chapter_url}")
    
    try:
        chapter_tab = main_tab.new_tab(chapter_url)
        time.sleep(2)
        
        # 检查是否在max_wait_time秒内获取到图片
        start_time = time.time()
        retry_count = 0
        max_retries = 3
        max_img_num = 0
        
        while retry_count <= max_retries:
            img_elements = chapter_tab.eles("xpath:" + xpaths['chapter_image_parent'])
            max_img_num = len(img_elements)
            
            if max_img_num > 0:
                print(f"章节{chapter_num}检测到{max_img_num}张图片")
                break
            
            elapsed = time.time() - start_time
            if elapsed >= max_wait_time:
                if retry_count < max_retries:
                    retry_count += 1
                    print(f"章节{chapter_num} ⚠️ {max_wait_time}秒内未检测到图片，第{retry_count}次重新加载页面...")
                    chapter_tab.get(chapter_url)
                    time.sleep(1)
                    start_time = time.time()
                else:
                    print(f"章节{chapter_num} ✗ 已达到最大重试次数({max_retries})，仍未检测到图片")
                    chapter_tab.close()
                    return {
                        'chapter_num': chapter_num,
                        'herf_list': []
                    }
            else:
                time.sleep(0.5)
        
        herf_list = get_chapter_image_urls_haoduoman(chapter_tab, max_img_num, xpaths, image_attr)
        
        chapter_tab.close()
        
    except Exception as e:
        print(f"处理章节{chapter_num}时出错: {e}")
        herf_list = []
    
    return {
        'chapter_num': chapter_num,
        'herf_list': herf_list
    }


def collect_chapters_images_haoduoman(self, target_comic_tab, chapter_start=1, chapter_end=0, max_threads=3, progress_callback=None):
    """好多漫完整章节收集逻辑 - 完全照抄"""
    print(f"设置最大同时收集线程数: {max_threads}")
    
    chapter_list_xpath = self.xpaths['chapter_list']
    chapter_eles = target_comic_tab.eles("xpath:" + chapter_list_xpath)
    all_chapters_num = len(chapter_eles)
    print(f"总章节数: {all_chapters_num}")
    
    first_chapter_xpath = self.xpaths['chapter_link'].replace("num", "1")
    first_chapter_ele = target_comic_tab.ele(f"xpath:{first_chapter_xpath}", timeout=5)
    first_chapter_href = first_chapter_ele.attr("href")
    print(f"第一个章节链接: {first_chapter_href}")
    
    # 计算实际下载范围
    actual_start = max(chapter_start, 1)
    actual_end = min(chapter_end, all_chapters_num) if chapter_end > 0 else all_chapters_num
    
    if actual_start > all_chapters_num:
        print(f"起始章节 {actual_start} 超过总章节数 {all_chapters_num}")
        return []
    
    actual_comic_num = actual_end
    print(f"将下载第 {actual_start}-{actual_end} 章，共 {actual_end - actual_start + 1} 章")
    
    all_chapters_data = []
    current_chapter = actual_start
    
    while current_chapter <= actual_comic_num:
        group_end = min(current_chapter + max_threads - 1, actual_comic_num)
        print(f"\n处理章节范围: {current_chapter}-{group_end}")
        
        batch_chapters_info = []
        for num in range(current_chapter, group_end + 1):
            chapter_url = re.sub(r'/\d+\.html$', f'/{num}.html', first_chapter_href)
            
            batch_chapters_info.append({
                'chapter_num': num,
                'url': chapter_url,
                'main_tab': self.tab
            })
            
            print(f"准备处理第{num}章节: {chapter_url}")
        
        threads = []
        results = []
        
        def thread_wrapper(chapter_info):
            result = collect_chapter_images_haoduoman(chapter_info, self.xpaths, self.image_attr)
            results.append(result)
        
        for chapter_info in batch_chapters_info:
            thread = threading.Thread(target=thread_wrapper, args=(chapter_info,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        all_chapters_data.extend(results)
        for _ in results:
            if progress_callback:
                progress_callback()
        current_chapter = group_end + 1
    
    return all_chapters_data


# ========== 御漫画完整逻辑 - 完全照抄 ==========

def click_show_more_yumanhua(crawler, target_comic_tab):
    """御漫画点击显示更多按钮 - 完全照抄"""
    try:
        show_more = target_comic_tab.ele(f"xpath:{crawler.xpaths['show_more_button']}")
        if show_more:
            print("找到'显示更多'按钮，准备点击...")
            show_more.scroll.to_see()
            time.sleep(0.3)
            show_more.click()
            print("✓ 已点击显示更多按钮")
            time.sleep(2)
            return True
        else:
            print("未找到'显示更多'按钮")
    except Exception as e:
        print(f"点击'显示更多'按钮失败: {e}")
    return False


def get_chapter_links_yumanhua(crawler, target_comic_tab):
    """御漫画获取章节链接 - 完全照抄"""
    print("正在获取章节列表...")
    
    click_show_more_yumanhua(crawler, target_comic_tab)
    
    chapter_elements = target_comic_tab.eles(f"xpath:{crawler.xpaths['chapter_list']}")
    total_chapters = len(chapter_elements)
    print(f"找到 {total_chapters} 个章节")
    
    chapter_links = []
    for i, chapter in enumerate(chapter_elements, 1):
        try:
            link_elem = chapter.ele(f"xpath:{crawler.xpaths['chapter_link']}")
            href = link_elem.attr("href")
            chapter_num = total_chapters - i + 1
            chapter_links.append({
                'num': chapter_num,
                'url': href
            })
        except Exception as e:
            print(f"获取第{i}个章节链接失败: {e}")
    
    chapter_links.sort(key=lambda x: x['num'])
    
    print(f"成功获取 {len(chapter_links)} 个章节链接")
    return chapter_links


def get_chapter_images_yumanhua(crawler, chapter_url, chapter_num=None, max_wait_time=3, max_page_retries=3):
    """御漫画获取单个章节图片
    
    Args:
        max_wait_time: 最大等待时间（秒），如果超过此时间未获取到图片则重新加载页面
        max_page_retries: 页面加载失败后的最大重试次数
    
    Returns:
        tuple: (image_urls, is_failed)
            - image_urls: 获取到的图片URL列表
            - is_failed: 是否获取失败（True表示完全失败，需要后续重试）
    """
    chapter_info = f"第 {chapter_num} 章" if chapter_num else ""
    print(f"正在获取{chapter_info}章节图片: {chapter_url}")
    
    # 尝试获取图片，如果3秒内未获取到则重新加载页面
    image_urls = []
    failed_indices = []
    max_images = 0
    
    for page_retry in range(max_page_retries + 1):
        # 加载页面
        crawler.tab.get(chapter_url)
        time.sleep(1)
        
        # 检查是否在max_wait_time秒内获取到图片
        start_time = time.time()
        images_found = False
        
        while time.time() - start_time < max_wait_time:
            image_divs = crawler.tab.eles(f"xpath:{crawler.xpaths['image_list']}")
            max_images = len(image_divs)
            
            if max_images > 0:
                images_found = True
                print(f"{chapter_info}页面本身有 {max_images} 张图片")
                break
            
            time.sleep(0.5)
        
        if images_found:
            break
        else:
            if page_retry < max_page_retries:
                print(f"{chapter_info}⚠️ {max_wait_time}秒内未检测到图片，第{page_retry + 1}次重新加载页面...")
            else:
                print(f"{chapter_info}✗ 已达到最大重试次数({max_page_retries})，仍未检测到图片")
                return [], True  # 返回失败标志
    
    # 获取图片URL - 一次性获取所有图片元素，避免重复查询
    print(f"{chapter_info}开始获取图片URL，共 {max_images} 张...")
    
    # 先一次性获取所有图片元素
    try:
        all_image_divs = crawler.tab.eles(f"xpath:{crawler.xpaths['image_list']}")
        print(f"{chapter_info}已获取到 {len(all_image_divs)} 个图片元素，开始提取URL...")
    except Exception as e:
        print(f"{chapter_info}✗ 获取图片元素列表失败: {e}")
        return [], True
    
    for i in range(1, max_images + 1):
        if i > len(all_image_divs):
            print(f"{chapter_info}✗ 第{i}张图片: 超过元素列表长度 {len(all_image_divs)}，停止获取")
            break
        
        try:
            img_div = all_image_divs[i-1]  # 直接使用已获取的元素
            # 在div中查找img标签
            img_elem = img_div.ele("tag:img")
            if not img_elem:
                failed_indices.append(i)
                print(f"{chapter_info}✗ 第{i}张图片: 未找到img标签")
                continue
                
            img_url = img_elem.attr(crawler.image_attr)
            if not img_url:
                img_url = img_elem.attr("src")
            if img_url:
                image_urls.append(img_url)
            else:
                failed_indices.append(i)
                print(f"{chapter_info}✗ 第{i}张图片: 没有找到URL")
        except Exception as e:
            failed_indices.append(i)
            print(f"{chapter_info}✗ 第{i}张图片: {e}")
    
    print(f"{chapter_info}本轮获取: {len(image_urls)}/{max_images} 张图片")
    
    # 如果有失败的图片，立即刷新页面重试一次
    if failed_indices and len(image_urls) < max_images:
        print(f"\n{chapter_info}有 {len(failed_indices)} 张图片获取失败，准备刷新页面重试...")
        
        crawler.tab.refresh()
        time.sleep(2)
        print(f"{chapter_info}页面已刷新，开始重试...")
        
        image_divs_new = crawler.tab.eles(f"xpath:{crawler.xpaths['image_list']}")
        max_images_new = len(image_divs_new)
        print(f"{chapter_info}刷新后检测到 {max_images_new} 张图片")
        
        for i in failed_indices[:]:
            if i > max_images_new:
                print(f"{chapter_info}✗ 第{i}张图片: 超过刷新后的最大图片数 {max_images_new}，跳过")
                continue
            
            try:
                img_div = image_divs_new[i-1]  # 直接使用已获取的元素
                img_elem = img_div.ele("tag:img")
                if not img_elem:
                    print(f"{chapter_info}✗ 第{i}张图片重试失败: 未找到img标签")
                    continue
                    
                img_url = img_elem.attr(crawler.image_attr)
                if not img_url:
                    img_url = img_elem.attr("src")
                if img_url:
                    image_urls.append(img_url)
                    failed_indices.remove(i)
                    print(f"{chapter_info}✓ 第{i}张图片重试成功")
                else:
                    print(f"{chapter_info}✗ 第{i}张图片重试失败: 没有找到URL")
            except Exception as e:
                print(f"{chapter_info}✗ 第{i}张图片重试失败: {e}")
    
    # 判断是否完全失败（一张图片都没获取到）
    is_failed = len(image_urls) == 0
    
    if is_failed:
        print(f"{chapter_info}✗ 完全失败，未获取到任何图片URL (页面本身有 {max_images} 张)")
    else:
        print(f"{chapter_info}✓ 最终成功获取 {len(image_urls)}/{max_images} 张图片URL")
    
    return image_urls, is_failed


def collect_chapters_images_yumanhua(self, target_comic_tab, chapter_start=1, chapter_end=0, max_workers=10, progress_callback=None):
    """御漫画完整章节收集逻辑
    
    Args:
        chapter_start: 起始章节号（从1开始）
        chapter_end: 结束章节号（0表示到最后一章）
    
    流程：
    1. 首次获取所有章节，3秒内未获取到URL的章节重新访问重试3次
    2. 记录完全失败的章节
    3. 等所有章节处理完成后，对失败章节再重试3次
    """
    chapter_links = get_chapter_links_yumanhua(self, target_comic_tab)
    total_found = len(chapter_links)
    print(f"获取到总共 {total_found} 个章节链接")
    
    # 根据章节范围筛选
    chapter_links = [c for c in chapter_links if c['num'] >= chapter_start]
    print(f"筛选起始章节 >= {chapter_start} 后，剩余 {len(chapter_links)} 个章节")
    
    if chapter_end > 0:
        chapter_links = [c for c in chapter_links if c['num'] <= chapter_end]
        print(f"筛选结束章节 <= {chapter_end} 后，剩余 {len(chapter_links)} 个章节")
    else:
        print(f"结束章节为0，下载到最后一章，剩余 {len(chapter_links)} 个章节")
    
    if chapter_links:
        actual_start = chapter_links[0]['num']
        actual_end = chapter_links[-1]['num']
        print(f"将下载第{actual_start}-{actual_end}章，共{len(chapter_links)}章")
    
    all_chapters_data = []
    failed_chapters = []  # 记录首次获取失败的章节
    total_chapters = len(chapter_links)
    
    # 使用队列来控制并发
    from queue import Queue
    import threading
    
    chapter_queue = Queue()
    for chapter_info in chapter_links:
        chapter_queue.put(chapter_info)
    
    results_lock = threading.Lock()
    
    # ========== 单浏览器多标签页模式 ==========
    print(f"\n使用单浏览器多标签页模式，最大并发 {max_workers} 个章节")
    
    def worker_thread(worker_id):
        """工作线程 - 每个线程有自己的标签页"""
        # 为每个工作线程创建一个独立的标签页
        worker_tab = self.tab.new_tab()
        
        worker_crawler = ComicCrawler(self.site_name, None, False)
        worker_crawler.tab = worker_tab
        worker_crawler.xpaths = self.xpaths
        worker_crawler.image_attr = self.image_attr
        
        print(f"[工作线程{worker_id}] 已创建标签页，开始处理章节...")
        
        while True:
            try:
                chapter_info = chapter_queue.get(block=False)
            except:
                break
            
            chapter_num = chapter_info['num']
            chapter_url = chapter_info['url']
            
            print(f"[工作线程{worker_id}] 正在处理第 {chapter_num} 章...")
            
            try:
                image_urls, is_failed = get_chapter_images_yumanhua(worker_crawler, chapter_url, chapter_num)
                
                with results_lock:
                    if is_failed:
                        print(f"[工作线程{worker_id}] 第 {chapter_num} 章首次获取完全失败，将后续重试")
                        failed_chapters.append(chapter_info)
                    elif image_urls:
                        all_chapters_data.append({
                            'chapter_num': chapter_num,
                            'herf_list': image_urls
                        })
                        print(f"[工作线程{worker_id}] 第 {chapter_num} 章: {len(image_urls)} 张图片")
                        if progress_callback:
                            progress_callback()
            except Exception as e:
                print(f"[工作线程{worker_id}] 处理第 {chapter_num} 章时出错: {e}")
                with results_lock:
                    failed_chapters.append(chapter_info)
            finally:
                chapter_queue.task_done()
        
        # 关闭工作线程的标签页
        worker_tab.close()
        print(f"[工作线程{worker_id}] 已完成并关闭标签页")
    
    # 同时创建所有工作线程
    print(f"\n启动 {max_workers} 个工作线程...")
    
    threads = []
    for i in range(max_workers):
        t = threading.Thread(target=worker_thread, args=(i,))
        threads.append(t)
        t.start()
    
    # 等待所有线程完成
    for t in threads:
        t.join()
    
    print(f"所有工作线程已完成")
    
    # 对首次失败的章节进行重试
    if failed_chapters:
        print(f"\n{'='*50}")
        print(f"首次获取完成，共有 {len(failed_chapters)} 个章节需要重试")
        print(f"{'='*50}")
        
        for retry_round in range(1, 4):  # 重试3次
            if not failed_chapters:
                break
            
            print(f"\n{'='*50}")
            print(f"第 {retry_round}/3 轮重试失败章节")
            print(f"{'='*50}")
            
            still_failed = []
            
            for chapter_info in failed_chapters:
                chapter_num = chapter_info['num']
                chapter_url = chapter_info['url']
                
                print(f"\n重试第 {chapter_num} 章...")
                
                try:
                    image_urls, is_failed = get_chapter_images_yumanhua(self, chapter_url, chapter_num)
                    
                    if is_failed:
                        print(f"第 {chapter_num} 章第{retry_round}轮重试仍然失败")
                        still_failed.append(chapter_info)
                    elif image_urls:
                        all_chapters_data.append({
                            'chapter_num': chapter_num,
                            'herf_list': image_urls
                        })
                        print(f"第 {chapter_num} 章重试成功: {len(image_urls)} 张图片")
                        if progress_callback:
                            progress_callback()
                except Exception as e:
                    print(f"重试第 {chapter_num} 章时出错: {e}")
                    still_failed.append(chapter_info)
            
            failed_chapters = still_failed
            print(f"\n第 {retry_round} 轮重试完成，仍有 {len(failed_chapters)} 个章节失败")
        
        # 最终失败的章节
        if failed_chapters:
            print(f"\n{'='*50}")
            print(f"⚠️ 以下章节经过3轮重试后仍然失败:")
            for chapter_info in failed_chapters:
                print(f"  - 第 {chapter_info['num']} 章: {chapter_info['url']}")
            print(f"{'='*50}")
    
    all_chapters_data.sort(key=lambda x: x['chapter_num'])
    
    print(f"\n{'='*50}")
    print(f"章节收集完成: 成功 {len(all_chapters_data)}/{total_chapters} 个章节")
    if failed_chapters:
        print(f"失败: {len(failed_chapters)} 个章节")
    print(f"{'='*50}")
    
    return all_chapters_data
