# 主脚本文件
# 整合所有模块，提供完整的漫画下载流程
from DrissionPage import ChromiumOptions, ChromiumPage
from urllib.parse import urlparse, unquote
import asyncio
from config import BROWSER_PATH, COMIC_SITE_URL
from crawler import collect_chapters_images
from downloader import download_all_chapters, download_cover_image
from utils import zip_main_folder


# 解析Cookie字符串的函数
def parse_cookie_str(cookie_str, domain):
    """解析Cookie字符串为DrissionPage可用的格式"""
    cookies = []
    items = [item.strip() for item in cookie_str.split(';') if item.strip()]
    
    for item in items:
        if '=' in item:
            name, value = item.split('=', 1)
            name = name.strip()
            value = value.strip()
            
            # 处理URL编码的值
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


def search_comic(tab, comic_name):
    """搜索漫画并返回详情页标签页"""
    # 打开漫画网站首页
    tab.get(COMIC_SITE_URL)

    # 在搜索框中输入漫画名称
    tab.ele("xpath:/html/body/div[1]/div/div/div/div[1]/div[2]/div/div[1]/input").input(comic_name)
    # 点击搜索按钮
    tab.ele("xpath:/html/body/div[1]/div/div/div/div[1]/div[2]/div/div[1]/a").click()
    # 点击第一个搜索结果
    target_comic_list = tab.ele("xpath:/html/body/div[1]/div/div/div/div[3]/div[1]/div[1]/div[1]/a/div[1]/img[1]")
    # 打开漫画详情页
    target_comic = target_comic_list.click.for_new_tab()

    return target_comic  # 返回漫画详情页标签页


def basic_info():
    """获取用户输入的漫画名称、章节数、浏览器选择和运行模式"""
    # 获取用户输入的漫画名称
    cookie = input("输入cookie (直接回车跳过): ").strip()
    comic_name = input("你想看什么漫画: ").strip().replace("' ", "").replace(" ", "")

    # 获取用户输入的cookie（可选）

    # 获取用户输入的章节数
    while True:
        comic_num_str = input("你想看第几张漫画: ").strip()
        if comic_num_str.isdigit() and int(comic_num_str) > 0:
            comic_num = int(comic_num_str)
            break
        else:
            print("请输入有效的章节数量！")

    # 获取用户选择的浏览器类型
    while True:
        browser_type = input("请选择浏览器类型 (1. Edge, 2. Chrome): ").strip()
        if browser_type in ["1", "2"]:
            browser_type = "edge" if browser_type == "1" else "chrome"
            break
        else:
            print("请输入有效的选项！")

    # 获取用户选择的运行模式
    while True:
        mode = input("请选择运行模式 (1. 有头模式, 2. 无头模式): ").strip()
        if mode in ["1", "2"]:
            headless = mode == "2"
            break
        else:
            print("请输入有效的选项！")

    # 获取浏览器路径
    default_browser_path = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" if browser_type == "edge" else "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    browser_path = input(f"请输入浏览器路径 (默认: {default_browser_path}): ").strip()
    if not browser_path:
        browser_path = default_browser_path
    
    return comic_name, comic_num, browser_type, headless, browser_path, cookie

def main():
    """主函数"""
    # 获取用户输入
    comic_name, comic_num, browser_type, headless, browser_path, cookie = basic_info()

    # 设置浏览器路径
    print(f"正在初始化{browser_type}浏览器...")
    co = ChromiumOptions().set_paths(browser_path)

    # 设置无头模式
    if headless:
        co.headless()
        # 添加无头模式必要的参数
        co.set_argument("--disable-gpu")
        co.set_argument("--no-sandbox")
        co.set_argument("--disable-dev-shm-usage")
        print("已启用无头模式")
    else:
        print("已启用有头模式")

    # 创建浏览器标签页
    tab = ChromiumPage(co)

    # 关键修复：先访问网站建立同域上下文
    print(f"访问网站: {COMIC_SITE_URL}")
    tab.get(COMIC_SITE_URL)

    # 如果有cookie，添加到浏览器
    if cookie:
        print("正在设置Cookie...")
        try:
            # 解析域名
            domain = urlparse(COMIC_SITE_URL).netloc
            
            # 解析Cookie字符串
            cookies = parse_cookie_str(cookie, domain)
            print(f"解析到 {len(cookies)} 个Cookie项")
            
            # 使用正确的API设置Cookie
            tab.set.cookies(cookies)
            print("Cookie已设置")
            
            # 刷新页面使Cookie生效
            print("刷新页面应用Cookie...")
            tab.refresh()
            print("Cookie已应用")
            
            # 刷新后重新搜索漫画
            print(f"正在搜索漫画: {comic_name}")
            tab.ele("xpath:/html/body/div[1]/div/div/div/div[1]/div[2]/div/div[1]/input").input(comic_name)
            tab.ele("xpath:/html/body/div[1]/div/div/div/div[1]/div[2]/div/div[1]/a").click()
            target_comic_list = tab.ele("xpath:/html/body/div[1]/div/div/div/div[3]/div[1]/div[1]/div[1]/a/div[1]/img[1]")
            target_comic_tab = target_comic_list.click.for_new_tab()
            print("成功打开漫画详情页")
        except Exception as e:
            print(f"设置Cookie失败: {str(e)}")
            # 如果设置Cookie失败，继续正常搜索
            target_comic_tab = search_comic(tab, comic_name)
    else:
        print("未提供Cookie，跳过设置")
        target_comic_tab = search_comic(tab, comic_name)
    
    print("Cookie已准备就绪")

    # 获取封面图片URL
    coverimg_xpath = "xpath:/html/body/div[1]/div/div/div/div[2]/div/div[1]/div/div[1]/img[3]"
    coverimg_url = target_comic_tab.ele(coverimg_xpath).attr("src")
    print(f"封面图片URL: {coverimg_url}")

    # 多线程收集所有章节的图片URL
    all_chapters_data = collect_chapters_images(target_comic_tab, comic_num)

    # 先下载封面图片
    if coverimg_url:
        asyncio.run(download_cover_image(coverimg_url, comic_name))

    # 协程下载所有章节的图片
    if all_chapters_data:
        asyncio.run(download_all_chapters(all_chapters_data, comic_name))
    else:
        print("没有获取到任何章节的图片链接，跳过下载")

    # 关闭主标签页
    tab.close()

    # 压缩主文件夹
    zip_main_folder(comic_name)

    input("按回车键结束程序...")


if __name__ == "__main__":
    main()
