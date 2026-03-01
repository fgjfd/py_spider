# 可视化界面模块 - 通用版
# 使用tkinter创建图形用户界面，整合漫画下载功能
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from DrissionPage import ChromiumOptions, ChromiumPage
from urllib.parse import urlparse, unquote
import asyncio
import threading
import os
import sys
import importlib.util


def import_module_from_path(module_name, file_path):
    """从文件路径导入模块"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class ComicDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("通用漫画下载器")
        self.root.geometry("650x700")
        self.root.resizable(True, True)
        
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 创建主框架
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建标题
        self.title_label = ttk.Label(
            self.main_frame, 
            text="通用漫画下载器", 
            font=("微软雅黑", 16, "bold")
        )
        self.title_label.pack(pady=10)
        
        # 创建输入区域
        self.input_frame = ttk.LabelFrame(self.main_frame, text="下载设置", padding="10")
        self.input_frame.pack(fill=tk.X, pady=5)
        
        # 网站选择
        self.site_frame = ttk.Frame(self.input_frame)
        self.site_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.site_frame, text="选择网站:", width=10).pack(side=tk.LEFT, padx=5)
        self.site_var = tk.StringVar(value="快看")
        site_combobox = ttk.Combobox(
            self.site_frame,
            textvariable=self.site_var,
            values=["快看", "好多漫"],
            state="readonly",
            font=("微软雅黑", 10),
            width=15
        )
        site_combobox.pack(side=tk.LEFT, padx=5)
        
        # 漫画名称输入
        self.name_frame = ttk.Frame(self.input_frame)
        self.name_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.name_frame, text="漫画名称:", width=10).pack(side=tk.LEFT, padx=5)
        self.comic_name_var = tk.StringVar()
        self.comic_name_entry = ttk.Entry(
            self.name_frame, 
            textvariable=self.comic_name_var, 
            font=("微软雅黑", 10)
        )
        self.comic_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Cookie输入
        self.cookie_frame = ttk.Frame(self.input_frame)
        self.cookie_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.cookie_frame, text="Cookie:", width=10).pack(side=tk.LEFT, padx=5)
        self.cookie_var = tk.StringVar()
        self.cookie_entry = ttk.Entry(
            self.cookie_frame, 
            textvariable=self.cookie_var, 
            font=("微软雅黑", 10)
        )
        self.cookie_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 章节数输入
        self.chapter_frame = ttk.Frame(self.input_frame)
        self.chapter_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.chapter_frame, text="章节数量:", width=10).pack(side=tk.LEFT, padx=5)
        self.comic_num_var = tk.StringVar(value="1")
        self.comic_num_entry = ttk.Entry(
            self.chapter_frame, 
            textvariable=self.comic_num_var, 
            font=("微软雅黑", 10),
            width=10
        )
        self.comic_num_entry.pack(side=tk.LEFT, padx=5)
        
        # 下载路径选择
        self.download_path_frame = ttk.Frame(self.input_frame)
        self.download_path_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.download_path_frame, text="下载路径:", width=10).pack(side=tk.LEFT, padx=5)
        self.download_path_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads"))
        self.download_path_entry = ttk.Entry(
            self.download_path_frame, 
            textvariable=self.download_path_var, 
            font=("微软雅黑", 10)
        )
        self.download_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        def browse_download_path():
            path = filedialog.askdirectory(
                title="选择下载路径",
                initialdir=self.download_path_var.get()
            )
            if path:
                self.download_path_var.set(path)
        
        ttk.Button(
            self.download_path_frame, 
            text="浏览", 
            command=browse_download_path,
            width=8
        ).pack(side=tk.LEFT, padx=5)
        
        # 浏览器选择
        self.browser_frame = ttk.LabelFrame(self.input_frame, text="浏览器设置", padding="10")
        self.browser_frame.pack(fill=tk.X, pady=5)
        
        # 浏览器类型选择
        self.browser_type_frame = ttk.Frame(self.browser_frame)
        self.browser_type_frame.pack(fill=tk.X, pady=3)
        
        ttk.Label(self.browser_type_frame, text="浏览器类型:", width=10).pack(side=tk.LEFT, padx=5)
        self.browser_type_var = tk.StringVar(value="edge")
        browser_type_frame_inner = ttk.Frame(self.browser_type_frame)
        browser_type_frame_inner.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Radiobutton(
            browser_type_frame_inner, 
            text="Edge", 
            variable=self.browser_type_var, 
            value="edge"
        ).pack(side=tk.LEFT, padx=10)
        
        ttk.Radiobutton(
            browser_type_frame_inner, 
            text="Chrome", 
            variable=self.browser_type_var, 
            value="chrome"
        ).pack(side=tk.LEFT, padx=10)
        
        # 浏览器路径
        self.browser_path_frame = ttk.Frame(self.browser_frame)
        self.browser_path_frame.pack(fill=tk.X, pady=3)
        
        ttk.Label(self.browser_path_frame, text="浏览器路径:", width=10).pack(side=tk.LEFT, padx=5)
        self.browser_path_var = tk.StringVar(value=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
        self.browser_path_entry = ttk.Entry(
            self.browser_path_frame, 
            textvariable=self.browser_path_var, 
            font=("微软雅黑", 10)
        )
        self.browser_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        def on_browser_type_change(*args):
            """当浏览器类型改变时更新默认路径"""
            browser_type = self.browser_type_var.get()
            if browser_type == "edge":
                default_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
            else:
                default_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            self.browser_path_var.set(default_path)
        
        # 监听浏览器类型变化
        self.browser_type_var.trace("w", on_browser_type_change)
        
        def browse_browser():
            path = filedialog.askopenfilename(
                title="选择浏览器可执行文件",
                filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
            )
            if path:
                self.browser_path_var.set(path)
        
        ttk.Button(
            self.browser_path_frame, 
            text="浏览", 
            command=browse_browser,
            width=8
        ).pack(side=tk.LEFT, padx=5)
        
        # 浏览器模式选择
        self.browser_mode_frame = ttk.Frame(self.browser_frame)
        self.browser_mode_frame.pack(fill=tk.X, pady=3)
        
        ttk.Label(self.browser_mode_frame, text="浏览器模式:", width=10).pack(side=tk.LEFT, padx=5)
        self.browser_mode_var = tk.StringVar(value="headed")
        browser_mode_frame_inner = ttk.Frame(self.browser_mode_frame)
        browser_mode_frame_inner.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Radiobutton(
            browser_mode_frame_inner, 
            text="有头模式", 
            variable=self.browser_mode_var, 
            value="headed"
        ).pack(side=tk.LEFT, padx=10)
        
        ttk.Radiobutton(
            browser_mode_frame_inner, 
            text="无头模式", 
            variable=self.browser_mode_var, 
            value="headless"
        ).pack(side=tk.LEFT, padx=10)
        
        # 按钮区域
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, pady=10)
        
        self.confirm_button = ttk.Button(
            self.button_frame, 
            text="确定", 
            command=self.start_download,
            style="Accent.TButton"
        )
        self.confirm_button.pack(side=tk.RIGHT, padx=5)
        
        self.clear_button = ttk.Button(
            self.button_frame, 
            text="清空状态", 
            command=self.clear_status
        )
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        self.exit_button = ttk.Button(
            self.button_frame, 
            text="退出", 
            command=root.quit
        )
        self.exit_button.pack(side=tk.RIGHT, padx=5)
        
        # 状态显示区域
        self.status_frame = ttk.LabelFrame(self.main_frame, text="下载状态", padding="10")
        self.status_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.status_text = tk.Text(
            self.status_frame, 
            font=("微软雅黑", 10),
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.status_text.pack(fill=tk.BOTH, expand=True)
        
        # 滚动条
        self.scrollbar = ttk.Scrollbar(self.status_text, command=self.status_text.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.config(yscrollcommand=self.scrollbar.set)
        
        # 配置样式
        self.style = ttk.Style()
        self.style.configure(
            "Accent.TButton", 
            foreground="black", 
            background="black",
            font=("微软雅黑", 10, "bold")
        )
        self.style.map(
            "Accent.TButton",
            background=[("active", "gray")]
        )
    
    def parse_cookie_str(self, cookie_str, domain):
        """解析Cookie字符串为DrissionPage可用的格式"""
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
    
    def append_status(self, text):
        """向状态文本框添加内容"""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, text + "\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
        self.root.update()
    
    def clear_status(self):
        """清空状态文本框"""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state=tk.DISABLED)
    
    def get_site_modules(self):
        """获取选中网站的模块"""
        site_name = self.site_var.get()
        if site_name == "快看":
            site_dir = os.path.join(self.base_path, "快看")
        else:
            site_dir = os.path.join(self.base_path, "好多漫漫画")
        
        config = import_module_from_path(f"{site_name}_config", os.path.join(site_dir, "config.py"))
        crawler = import_module_from_path(f"{site_name}_crawler", os.path.join(site_dir, "crawler.py"))
        downloader = import_module_from_path(f"{site_name}_downloader", os.path.join(site_dir, "downloader.py"))
        utils = import_module_from_path(f"{site_name}_utils", os.path.join(site_dir, "utils.py"))
        
        return config, crawler, downloader, utils
    
    def download_task(self):
        """下载任务函数"""
        try:
            config, crawler, downloader, utils = self.get_site_modules()
            
            # 获取用户输入
            comic_name = self.comic_name_var.get().strip()
            if not comic_name:
                messagebox.showerror("错误", "请输入漫画名称")
                return
            
            comic_num_str = self.comic_num_var.get().strip()
            if not comic_num_str.isdigit() or int(comic_num_str) <= 0:
                messagebox.showerror("错误", "请输入有效的章节数量")
                return
            comic_num = int(comic_num_str)
            
            browser_path = self.browser_path_var.get().strip()
            if not browser_path or not os.path.exists(browser_path):
                messagebox.showerror("错误", "浏览器路径无效")
                return
            
            browser_mode = self.browser_mode_var.get()
            browser_type = self.browser_type_var.get()
            
            self.confirm_button.config(state=tk.DISABLED)
            
            self.append_status(f"正在初始化浏览器... (类型: {browser_type}, 模式: {browser_mode})")
            co = ChromiumOptions().set_paths(browser_path)
            
            if browser_mode == "headless":
                co.headless()
                co.set_argument("--disable-gpu")
                co.set_argument("--no-sandbox")
                co.set_argument("--disable-dev-shm-usage")
                self.append_status("已启用无头模式")
            
            tab = ChromiumPage(co)
            cookie = self.cookie_var.get().strip()
            site_name = self.site_var.get()
            
            try:
                self.append_status(f"访问网站: {config.COMIC_SITE_URL}")
                tab.get(config.COMIC_SITE_URL)
                
                if cookie:
                    self.append_status("正在设置Cookie...")
                    try:
                        domain = urlparse(config.COMIC_SITE_URL).netloc
                        cookies = self.parse_cookie_str(cookie, domain)
                        self.append_status(f"解析到 {len(cookies)} 个Cookie项")
                        tab.set.cookies(cookies)
                        self.append_status("Cookie已设置")
                        self.append_status("刷新页面应用Cookie...")
                        tab.refresh()
                        self.append_status("Cookie已应用")
                        
                        self.append_status(f"正在搜索漫画: {comic_name}")
                        tab.ele(f"xpath:{config.XPATHS['search_input']}").input(comic_name)
                        tab.ele(f"xpath:{config.XPATHS['search_button']}").click()
                        import time
                        time.sleep(0.5)
                        target_comic_list = tab.ele(f"xpath:{config.XPATHS['search_result']}")
                        
                        if site_name == "快看":
                            target_comic_tab = target_comic_list.click.for_new_tab()
                        else:
                            href = target_comic_list.attr('href')
                            target_comic_tab = tab.new_tab(href)
                        
                        self.append_status("成功打开漫画详情页")
                    except Exception as e:
                        self.append_status(f"设置Cookie失败: {str(e)}")
                        self.append_status(f"正在搜索漫画: {comic_name}")
                        tab.ele(f"xpath:{config.XPATHS['search_input']}").input(comic_name)
                        tab.ele(f"xpath:{config.XPATHS['search_button']}").click()
                        import time
                        time.sleep(0.5)
                        target_comic_list = tab.ele(f"xpath:{config.XPATHS['search_result']}")
                        
                        if site_name == "快看":
                            target_comic_tab = target_comic_list.click.for_new_tab()
                        else:
                            href = target_comic_list.attr('href')
                            target_comic_tab = tab.new_tab(href)
                        
                        self.append_status("成功打开漫画详情页")
                else:
                    self.append_status("未提供Cookie，跳过设置")
                    self.append_status(f"正在搜索漫画: {comic_name}")
                    tab.ele(f"xpath:{config.XPATHS['search_input']}").input(comic_name)
                    tab.ele(f"xpath:{config.XPATHS['search_button']}").click()
                    import time
                    time.sleep(0.5)
                    target_comic_list = tab.ele(f"xpath:{config.XPATHS['search_result']}")
                    
                    if site_name == "快看":
                        target_comic_tab = target_comic_list.click.for_new_tab()
                    else:
                        href = target_comic_list.attr('href')
                        target_comic_tab = tab.new_tab(href)
                    
                    self.append_status("成功打开漫画详情页")
                
                self.append_status("Cookie已准备就绪")
                
                try:
                    coverimg_xpath = "xpath:" + config.XPATHS['cover_image']
                    coverimg_url = target_comic_tab.ele(coverimg_xpath).attr("src")
                    self.append_status(f"封面图片URL: {coverimg_url}")
                except Exception as e:
                    self.append_status(f"获取封面图片失败: {e}")
                    coverimg_url = None
                
                self.append_status(f"正在收集第1-{comic_num}章的图片链接...")
                
                if site_name == "快看":
                    all_chapters_data = crawler.collect_chapters_images(target_comic_tab, comic_num)
                else:
                    all_chapters_data = crawler.collect_chapters_images(target_comic_tab, comic_num, tab)
                
                if all_chapters_data:
                    self.append_status(f"成功收集到 {len(all_chapters_data)} 个章节的图片链接")
                else:
                    self.append_status("没有获取到任何章节的图片链接")
                
                download_path = self.download_path_var.get().strip()
                
                if coverimg_url:
                    self.append_status(f"正在下载封面图片...")
                    asyncio.run(downloader.download_cover_image(coverimg_url, comic_name, download_path if download_path else None))
                    self.append_status("封面图片下载完成")
                
                if all_chapters_data:
                    self.append_status("正在下载章节图片...")
                    asyncio.run(downloader.download_all_chapters(all_chapters_data, comic_name, download_path if download_path else None))
                    self.append_status("章节图片下载完成")
                
                self.append_status("正在压缩文件夹...")
                utils.zip_main_folder(comic_name, download_path if download_path else None)
                self.append_status("文件夹压缩完成")
                
                messagebox.showinfo("成功", f"漫画 {comic_name} 下载完成！")
                
            finally:
                tab.close()
                self.append_status("浏览器已关闭")
                
        except Exception as e:
            self.append_status(f"下载过程中出错: {e}")
            import traceback
            self.append_status(traceback.format_exc())
            messagebox.showerror("错误", f"下载过程中出错: {e}")
        finally:
            self.confirm_button.config(state=tk.NORMAL)
    
    def start_download(self):
        """开始下载"""
        download_thread = threading.Thread(target=self.download_task)
        download_thread.daemon = True
        download_thread.start()


def main():
    """主函数"""
    root = tk.Tk()
    app = ComicDownloaderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
