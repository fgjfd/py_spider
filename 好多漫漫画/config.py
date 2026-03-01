# 配置文件 - 好多漫
# 存储所有配置参数和XPath信息

BROWSER_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

COMIC_SITE_URL = "https://www.haoduoman.com/"

MAX_RETRIES = 5

MAX_RETRY = 3

WAIT_TIME = 0.1

MAX_THREADS = 3

CONCURRENT_DOWNLOAD_LIMIT = 10

DOWNLOAD_DELAY = 0.2

XPATHS = {
    "search_input": "/html/body/header/div[2]/div/div[2]/div/form/div/p[1]/input",
    "search_button": "/html/body/header/div[2]/div/div[2]/div/form/div/p[2]/button",
    "search_result": "/html/body/main/div/div[2]/div/div[1]/div/div/div[2]/a",
    "cover_image": "/html/body/main/div/div[2]/div[1]/div/div/div/div[1]/img",
    "chapter_list": "/html/body/main/div/div[3]/div[2]/ul/li",
    "chapter_link": "/html/body/main/div/div[3]/div[2]/ul/li[num]/a",
    "chapter_image_parent": "/html/body/main/div[1]/div/div[1]/div",
    "chapter_image_data_original": "/html/body/main/div[1]/div/div[1]/div[num]"
}
