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
        elif self.site_name == '拷贝漫画':
            return self.search_comic_mangacopy(comic_name)
    
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
    
    def search_comic_mangacopy(self, comic_name):
        """拷贝漫画搜索逻辑 - 直接访问搜索URL"""
        # 直接访问搜索URL
        search_url = f"https://www.mangacopy.com/search?q={comic_name}&q_type="
        print(f"正在搜索漫画: {comic_name}")
        print(f"搜索URL: {search_url}")
        
        self.tab.get(search_url)
        time.sleep(2)
        
        print(f"开始查找搜索结果...")
        print(f"使用的XPath: {self.xpaths['search_result']}")
        
        max_wait_time = 15
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                result = self.tab.ele(f"xpath:{self.xpaths['search_result']}", timeout=0)
                if result:
                    print(f"找到搜索结果元素")
                    href = result.attr('href')
                    print(f"搜索结果链接: {href}")
                    if href:
                        print(f"正在打开漫画详情页: {href}")
                        target_comic_tab = self.page.new_tab(href)
                        print("已打开漫画详情页")
                        return target_comic_tab
                    else:
                        print("搜索结果元素没有href属性")
                else:
                    print("未找到搜索结果元素")
            except Exception as e:
                print(f"查找搜索结果时出错: {e}")
            
            print(f"等待搜索结果... ({int(time.time() - start_time)}s/{max_wait_time}s)")
            time.sleep(1)
        
        print(f"超时！当前页面URL: {self.tab.url}")
        print(f"当前页面标题: {self.tab.title}")
        
        raise Exception(f"搜索漫画 '{comic_name}' 超时，未找到搜索结果")
    
    def get_cover_image(self, target_comic_tab):
        """获取封面图片"""
        try:
            coverimg_xpath = "xpath:" + self.xpaths['cover_image']
            coverimg_url = target_comic_tab.ele(coverimg_xpath).attr(self.image_attr)
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
        elif self.site_name == '拷贝漫画':
            chapter_list_xpath = self.xpaths['chapter_list']
            chapter_eles = target_comic_tab.eles("xpath:" + chapter_list_xpath)
            return len(chapter_eles)
        return 0
    
    def collect_chapters_images(self, target_comic_tab, chapter_start=1, chapter_end=0, max_workers=10, progress_callback=None):
        """收集章节图片 - 根据站点使用不同逻辑
        
        Args:
            chapter_start: 起始章节号（从1开始）
            chapter_end: 结束章节号（0表示到最后一章）
        """
        if self.site_name == '快看':
            return collect_chapters_images_kuaikan(self, target_comic_tab, chapter_start, chapter_end, max_workers, progress_callback)
        elif self.site_name == '好多漫':
            return collect_chapters_images_haoduoman(self, target_comic_tab, chapter_start, chapter_end, max_workers, progress_callback)
        elif self.site_name == '拷贝漫画':
            return collect_chapters_images_mangacopy(self, target_comic_tab, chapter_start, chapter_end, max_workers, progress_callback)


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


# ========== 拷贝漫画完整逻辑 ==========

def get_chapter_image_urls_mangacopy(chapter_tab, max_img_num, xpaths, image_attr):
    """拷贝漫画获取单个章节图片URL - 先滚动到底部再获取"""
    herf_list = []
    
    try:
        # 1. 获取页面显示的最大图片数（从文本中获取）
        try:
            max_img_text = chapter_tab.ele("xpath:/html/body/div[1]/span[2]", timeout=3).text
            expected_img_num = int(max_img_text.strip())
            print(f"页面显示最大图片数: {expected_img_num}")
        except Exception as e:
            print(f"无法获取最大图片数，使用传入值: {max_img_num}")
            expected_img_num = max_img_num
        
        # 2. 模拟鼠标滚动触发懒加载，直到图片数正常
        print("开始模拟鼠标滚动触发懒加载...")
        scroll_step = 300  # 每次滚动的像素
        max_scrolls = expected_img_num * 2  # 最大滚动次数
        scroll_count = 0
        
        while scroll_count < max_scrolls:
            # 每次重新获取DOM检测当前图片数
            img_elements = chapter_tab.eles("xpath:" + xpaths['chapter_image_parent'])
            actual_img_num = len(img_elements)
            
            print(f"当前已加载{actual_img_num}张图片，目标{expected_img_num}张，已滚动{scroll_count}次")
            
            # 如果图片数达到目标，停止滑动
            if actual_img_num >= expected_img_num:
                print(f"✓ 已加载所有图片 ({actual_img_num}/{expected_img_num})")
                break
            
            # 模拟鼠标向下滚动
            chapter_tab.scroll.down(scroll_step)
            time.sleep(0.5)  # 等待页面加载
            scroll_count += 1
        
        # 3. 最终获取图片数量
        img_elements = chapter_tab.eles("xpath:" + xpaths['chapter_image_parent'])
        actual_img_num = len(img_elements)
        
        print(f"最终检测到{actual_img_num}张图片")
        
        if actual_img_num < expected_img_num:
            print(f"⚠️ 实际图片数({actual_img_num})少于预期({expected_img_num})")
            # 保存网页HTML用于调试
            try:
                html_content = chapter_tab.html
                debug_file = f"chapter_{expected_img_num}_debug.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print(f"已保存网页HTML到: {debug_file}")
            except Exception as e:
                print(f"保存HTML失败: {e}")
        
        # 4. 遍历图片获取URL，使用 /html/body/div[2]/div/ul/li[num]/img
        print(f"开始获取图片URL，共{actual_img_num}张...")
        for num in range(1, actual_img_num + 1):
            try:
                img_xpath = f"/html/body/div[2]/div/ul/li[{num}]/img"
                img_ele = chapter_tab.ele(f"xpath:{img_xpath}", timeout=3)
                herf = img_ele.attr('data-src')
                
                if is_normal_url(herf):
                    print(f"第{num}张图片: {herf}")
                    herf_list.append(herf)
                else:
                    print(f"第{num}张图片URL无效: {herf}")
                    
            except Exception as e:
                print(f"获取第{num}张图片时出错: {e}")
    
    except Exception as e:
        print(f"获取图片列表时出错: {e}")
    
    return herf_list


def collect_chapter_images_mangacopy(chapter_info, xpaths, image_attr, max_wait_time=3):
    """拷贝漫画收集单个章节
    
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
        
        herf_list = get_chapter_image_urls_mangacopy(chapter_tab, max_img_num, xpaths, image_attr)
        
        chapter_tab.close()
        
    except Exception as e:
        print(f"处理章节{chapter_num}时出错: {e}")
        herf_list = []
    
    return {
        'chapter_num': chapter_num,
        'herf_list': herf_list
    }


def collect_chapters_images_mangacopy(self, target_comic_tab, chapter_start=1, chapter_end=0, max_threads=3, progress_callback=None):
    """拷贝漫画完整章节收集逻辑"""
    print(f"设置最大同时收集线程数: {max_threads}")
    
    chapter_list_xpath = self.xpaths['chapter_list']
    chapter_eles = target_comic_tab.eles("xpath:" + chapter_list_xpath)
    all_chapters_num = len(chapter_eles)
    print(f"总章节数: {all_chapters_num}")
    
    chapter_urls = []
    for i, chapter_ele in enumerate(chapter_eles, 1):
        href = chapter_ele.attr('href')
        chapter_urls.append(href)
        print(f"章节{i}: {href}")
    
    if not chapter_urls:
        print("未找到任何章节链接")
        return []
    
    actual_start = max(chapter_start, 1)
    actual_end = min(chapter_end, all_chapters_num) if chapter_end > 0 else all_chapters_num
    
    if actual_start > all_chapters_num:
        print(f"起始章节 {actual_start} 超过总章节数 {all_chapters_num}")
        return []
    
    print(f"将下载第 {actual_start}-{actual_end} 章，共 {actual_end - actual_start + 1} 章")
    
    all_chapters_data = []
    current_chapter = actual_start
    
    while current_chapter <= actual_end:
        group_end = min(current_chapter + max_threads - 1, actual_end)
        print(f"\n处理章节范围: {current_chapter}-{group_end}")
        
        batch_chapters_info = []
        for num in range(current_chapter, group_end + 1):
            chapter_url = chapter_urls[num - 1]
            
            batch_chapters_info.append({
                'chapter_num': num,
                'url': chapter_url,
                'main_tab': self.tab
            })
            
            print(f"准备处理第{num}章节: {chapter_url}")
        
        threads = []
        results = []
        
        def thread_wrapper(chapter_info):
            result = collect_chapter_images_mangacopy(chapter_info, self.xpaths, self.image_attr)
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
