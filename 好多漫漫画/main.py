# 主脚本文件 - 好多漫
# 整合所有模块，提供完整的漫画下载流程
from DrissionPage import ChromiumOptions, ChromiumPage
import asyncio
import time
from config import BROWSER_PATH, COMIC_SITE_URL, XPATHS
from crawler import collect_chapters_images
from downloader import download_all_chapters, download_cover_image
from utils import zip_main_folder


def search_comic(tab, comic_name):
    """搜索漫画并返回详情页标签页"""
    tab.get(COMIC_SITE_URL)

    tab.ele(f"xpath:{XPATHS['search_input']}").input(comic_name)
    tab.ele(f"xpath:{XPATHS['search_button']}").click()
    
    time.sleep(0.5)
    
    target_comic_list = tab.ele(f"xpath:{XPATHS['search_result']}")
    href = target_comic_list.attr('href')
    target_comic = tab.new_tab(href)

    return target_comic


def basic_info():
    """获取用户输入的漫画名称、章节数、浏览器选择和运行模式"""
    comic_name = input("你想看什么漫画: ").strip().replace("' ", "").replace(" ", "")

    while True:
        comic_num_str = input("你想看第几张漫画: ").strip()
        if comic_num_str.isdigit() and int(comic_num_str) > 0:
            comic_num = int(comic_num_str)
            break
        else:
            print("请输入有效的章节数量！")

    while True:
        browser_type = input("请选择浏览器类型 (1. Edge, 2. Chrome): ").strip()
        if browser_type in ["1", "2"]:
            browser_type = "edge" if browser_type == "1" else "chrome"
            break
        else:
            print("请输入有效的选项！")

    while True:
        mode = input("请选择运行模式 (1. 有头模式, 2. 无头模式): ").strip()
        if mode in ["1", "2"]:
            headless = mode == "2"
            break
        else:
            print("请输入有效的选项！")

    default_browser_path = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" if browser_type == "edge" else "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    browser_path = input(f"请输入浏览器路径 (默认: {default_browser_path}): ").strip()
    if not browser_path:
        browser_path = default_browser_path
    
    return comic_name, comic_num, browser_type, headless, browser_path


def main():
    """主函数"""
    comic_name, comic_num, browser_type, headless, browser_path = basic_info()

    print(f"正在初始化{browser_type}浏览器...")
    co = ChromiumOptions().set_paths(browser_path)

    if headless:
        co.headless()
        co.set_argument("--disable-gpu")
        co.set_argument("--no-sandbox")
        co.set_argument("--disable-dev-shm-usage")
        print("已启用无头模式")
    else:
        print("已启用有头模式")

    tab = ChromiumPage(co)

    print(f"访问网站: {COMIC_SITE_URL}")
    tab.get(COMIC_SITE_URL)

    print("正在搜索漫画: " + comic_name)
    target_comic_tab = search_comic(tab, comic_name)
    print("成功打开漫画详情页")

    try:
        coverimg_xpath = "xpath:" + XPATHS['cover_image']
        coverimg_url = target_comic_tab.ele(coverimg_xpath).attr("src")
        print(f"封面图片URL: {coverimg_url}")
    except Exception as e:
        print(f"获取封面图片失败: {e}")
        coverimg_url = None

    all_chapters_data = collect_chapters_images(target_comic_tab, comic_num, tab)

    if coverimg_url:
        asyncio.run(download_cover_image(coverimg_url, comic_name))

    if all_chapters_data:
        asyncio.run(download_all_chapters(all_chapters_data, comic_name))
    else:
        print("没有获取到任何章节的图片链接，跳过下载")

    tab.close()

    zip_main_folder(comic_name)

    input("按回车键结束程序...")


if __name__ == "__main__":
    main()
