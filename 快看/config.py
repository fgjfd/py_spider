# 配置文件
# 存储所有配置参数，方便统一管理和修改

# 浏览器路径
# 设置Edge浏览器的可执行文件路径
BROWSER_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# 漫画网站URL
# 设置要爬取的漫画网站地址
COMIC_SITE_URL = "https://www.kuaikanmanhua.com/"

# 最大重试次数
# 获取图片URL时的最大重试次数
MAX_RETRIES = 5

# 重新尝试次数
# 重新获取失败图片的最大尝试次数
MAX_RETRY = 3

# 等待时间
# 页面加载和元素获取之间的等待时间（秒）
WAIT_TIME = 0.1

# 最大线程数
# 并发收集章节图片URL的最大线程数
MAX_THREADS = 3

# 并发下载限制
# 异步下载图片时的最大并发数
CONCURRENT_DOWNLOAD_LIMIT = 10

# 延迟时间
# 每批下载任务之间的延迟时间（秒）
DOWNLOAD_DELAY = 0.2
