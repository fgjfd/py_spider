# 爬虫模块
# 实现获取图片链接、重试失败图片、多线程收集章节等功能
import time
import threading
from os.path import split

from config import MAX_RETRIES, MAX_RETRY, WAIT_TIME, MAX_THREADS
from utils import is_normal_url


def retry_failed_image(chapter_tab, pic_des, num, wait_time, max_retry=MAX_RETRY):
    """重新尝试获取单个失败的图片"""
    # 替换图片描述中的num为实际图片序号
    current_pic_des = pic_des.replace("num", str(num))
    herf = None
    retry_count = 0
    
    # 最多尝试max_retry次
    while retry_count < max_retry:
        try:
            print(f"重新尝试获取第{num}张图片 (尝试 {retry_count + 1}/{max_retry})")
            # 尝试获取元素
            img_ele = chapter_tab.ele(f"xpath:{current_pic_des}", timeout=3)
            
            # 滚动到元素使其可见
            chapter_tab.scroll.to_see(img_ele)
            
            # 等待加载
            time.sleep(wait_time)
            
            # 获取链接
            herf = img_ele.attr("src")
            
            if is_normal_url(herf):
                print(f"重新获取第{num}张图片成功: {herf}")
                return herf
            else:
                print(f"重新获取第{num}张图片(非正常): {herf}")
                retry_count += 1
                time.sleep(0.5)
        except Exception as e:
            print(f"重新获取第{num}张图片时出错: {e}")
            retry_count += 1
            time.sleep(0.5)
    
    if not herf or not is_normal_url(herf):
        print(f"第{num}张图片: 重新尝试{max_retry}次后仍未获取到有效URL")
    
    return herf


def get_pic_herf(pic_tab, pic_des, wait_time, max_num, max_retries=MAX_RETRIES):
    """获取单个章节的图片URL列表"""
    herf_list = []
    failed_indices = []

    print("开始爬取")
    start_time = time.time()

    # 逐个处理元素
    for num in range(1, max_num + 1):
        current_pic_des = pic_des.replace("num", str(num))
        herf = None
        retry_count = 0

        # 最多尝试max_retries次
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
            herf_list.append(None)  # 保留位置，保持顺序
            failed_indices.append(num - 1)  # 记录失败的索引（从0开始）

    end_time = time.time()
    print("\nover")
    print(f"耗时: {end_time - start_time} 秒")
    print(f"共获取{len([h for h in herf_list if h])}张图片，{len(failed_indices)}张失败")

    # 打印保存的链接
    print("\n保存的链接:")
    for i, herf in enumerate(herf_list, 1):
        if herf:
            print(f"{i}: {herf}")
        else:
            print(f"{i}: 获取失败")

    return herf_list, failed_indices


def collect_chapter_images(chapter_info):
    """收集单个章节的图片URL"""
    chapter_num = chapter_info['chapter_num']
    chapter_tab = chapter_info['tab']
    max_img_num = chapter_info['max_img_num']
    
    # 使用XPath获取图片
    pic_des = "/html/body/div[1]/div/div/div/div[4]/div[1]/div[1]/div[num]/img[1]"
    
    # 获取图片链接
    herf_list, failed_indices = get_pic_herf(chapter_tab, pic_des, wait_time=WAIT_TIME, max_num=max_img_num, max_retries=MAX_RETRIES)
    
    # 重新获取失败的图片
    if failed_indices:
        print(f"\n开始重新获取章节{chapter_num}的失败图片...")
        for idx in failed_indices:
            num = idx + 1  # 转换为原始图片序号
            herf = retry_failed_image(chapter_tab, pic_des, num, wait_time=WAIT_TIME)
            if herf and is_normal_url(herf):
                herf_list[idx] = herf  # 更新到原列表中，保持顺序
    
    # 关闭标签页
    chapter_tab.close()
    
    return {
        'chapter_num': chapter_num,
        'herf_list': [h for h in herf_list if h]  # 过滤掉None值，只保留成功获取的链接
    }


def collect_chapters_images(target_comic_tab, comic_num, max_threads=MAX_THREADS):
    """多线程收集所有章节的图片URL"""
    print(f"设置最大同时收集线程数: {max_threads}")

    # 首先获取漫画信息，确定实际可下载的章节数
    chapter_num_group_xpaths_list, _, all_chapters_num, _ = collect_all_chapters_xpath(target_comic_tab)

    # 如果需求数大于总章节数，则下载最大数量
    actual_comic_num = min(comic_num, all_chapters_num)
    print(f"用户请求下载 {comic_num} 章，实际可下载 {actual_comic_num} 章（总章节数: {all_chapters_num}）")

    # 初始化所有章节数据列表
    all_chapters_data = []
    # 每组包含50个章节
    one_group_chapter_num = 50

    # 从第1章开始处理
    current_chapter = 1
    # 循环处理直到下载完所有需要的章节
    while current_chapter <= actual_comic_num:
        # 计算当前组的结束章节，取当前组最大章节和实际需要章节的较小值
        group_end = min(current_chapter + one_group_chapter_num - 1, actual_comic_num)

        # 计算当前组的索引（从0开始）
        group_index = (current_chapter - 1) // one_group_chapter_num

        # 如果不是第一组，需要点击对应的组按钮来切换显示
        if group_index > 0:
            # 获取当前组按钮的xpath
            group_xpath = chapter_num_group_xpaths_list[group_index]
            try:
                # 找到组按钮元素
                group_ele = target_comic_tab.ele(f"xpath:{group_xpath}")
                # 点击组按钮
                group_ele.click()
                # 打印切换信息
                print(f"点击第 {group_index + 1} 组按钮，显示章节 {current_chapter}-{group_end}")
                # 等待页面加载完成
                time.sleep(1)
            except Exception as e:
                # 点击失败时打印错误信息并退出循环
                print(f"点击第 {group_index + 1} 组按钮时出错: {e}")
                break

        # 获取当前组内需要下载的章节xpath列表
        _, chapter_xpaths, _, _ = collect_all_chapters_xpath(target_comic_tab, current_chapter, group_end)

        # 打印当前组处理信息
        print(f"\n开始处理第 {group_index + 1} 组，章节范围: {current_chapter}-{group_end}")

        # 按批次处理当前组的章节，每批最多max_threads个章节
        for i in range(0, len(chapter_xpaths), max_threads):
            # 获取当前批次的章节列表
            batch = chapter_xpaths[i:i + max_threads]
            # 打印批次信息
            print(f"\n处理批次 {i // max_threads + 1}: 章节 {[chap[0] for chap in batch]}")

            # 初始化当前批次的章节信息列表
            batch_chapters_info = []
            # 遍历当前批次的每个章节
            for num, xpath in batch:
                try:
                    # 找到章节元素
                    chapter_ele = target_comic_tab.ele(f"xpath:{xpath}")
                    # 点击章节并在新标签页中打开
                    chapter_tab = chapter_ele.click.for_new_tab()

                    # 获取章节中的图片元素列表
                    img_elements = chapter_tab.eles("xpath:/html/body/div/div/div/div/div[4]/div[1]/div[1]/div/img[1]")

                    # 统计图片数量
                    max_img_num = len(img_elements)

                    # 将章节信息添加到批次列表中
                    batch_chapters_info.append({
                        'chapter_num': num,
                        'tab': chapter_tab,
                        'max_img_num': max_img_num
                    })

                    # 打印章节打开信息
                    print(f"打开第{num}章节，检测到{max_img_num}张图片")

                except Exception as e:
                    # 打开章节失败时打印错误信息
                    print(f"打开第{num}章节时出错: {e}")

            # 初始化线程列表
            threads = []
            # 初始化结果列表
            results = []

            # 定义线程包装函数，用于收集线程结果
            def thread_wrapper(chapter_info):
                # 调用章节图片收集函数
                result = collect_chapter_images(chapter_info)
                # 将结果添加到结果列表
                results.append(result)

            # 为当前批次的每个章节创建并启动线程
            for chapter_info in batch_chapters_info:
                # 创建线程
                thread = threading.Thread(target=thread_wrapper, args=(chapter_info,))
                # 将线程添加到线程列表
                threads.append(thread)
                # 启动线程
                thread.start()

            # 等待当前批次的所有线程完成
            for thread in threads:
                # 等待线程结束
                thread.join()

            # 将当前批次的结果添加到总结果中
            all_chapters_data.extend(results)

        # 更新当前章节为下一组的起始章节
        current_chapter = group_end + 1

    # 返回所有章节的图片数据
    return all_chapters_data

def collect_all_chapters_xpath(target_comic_tab, start_chapter=1, end_chapter=50):
    """
    获取指定范围章节的xpath列表
    start_chapter: 起始章节号
    end_chapter: 结束章节号
    """
    # 每组包含50个章节
    one_group_chapter_num = 50

    # 章节组按钮的xpath
    chapter_num_group_xpaths = "/html/body/div[1]/div/div/div/div[2]/div/div[2]/div[1]/div[1]/div/div[2]/div"
    # 获取所有章节组按钮元素
    chapter_num_group_eles = target_comic_tab.eles("xpath:" + chapter_num_group_xpaths)
    # 统计组按钮数量
    group_num = len(chapter_num_group_eles)

    # 初始化章节组按钮xpath列表
    chapter_num_group_xpaths_list = []

    # 遍历所有组按钮，生成对应的xpath
    for num in range(1, group_num + 1):
        # 生成第num个组按钮的xpath
        chapter_xpath = f"/html/body/div[1]/div/div/div/div[2]/div/div[2]/div[1]/div[1]/div/div[2]/div[{num}]"
        # 将xpath添加到列表中
        chapter_num_group_xpaths_list.append(chapter_xpath)

    # 获取最后一个组按钮的xpath
    goal_xpath = "xpath:" + chapter_num_group_xpaths_list[-1]
    # 获取最后一个组按钮的文本内容
    num_text = target_comic_tab.ele(goal_xpath).text
    # 解析文本获取总章节数
    all_chapters_num = int(num_text.replace(" ", "").split("-")[1])
    # 计算最后一组的章节数量
    last_chapters_num = all_chapters_num - int(num_text.replace(" ", "").split("-")[0]) + 1

    # 计算起始章节所在的组索引（从0开始）
    current_group_index = (start_chapter - 1) // one_group_chapter_num
    # 计算当前组的起始章节号
    group_start_chapter = current_group_index * one_group_chapter_num + 1
    # 计算当前组的结束章节号，取最大值和总章节数的较小值
    group_end_chapter = min((current_group_index + 1) * one_group_chapter_num, all_chapters_num)

    # 计算实际需要下载的起始章节
    actual_start = max(start_chapter, group_start_chapter)
    # 计算实际需要下载的结束章节
    actual_end = min(end_chapter, group_end_chapter)

    # 初始化章节xpath列表
    chapter_xpaths = []
    # 遍历需要下载的章节范围
    for num in range(actual_start, actual_end + 1):
        # 计算章节在当前组内的相对位置
        relative_num = num - group_start_chapter + 1
        # 生成章节的xpath
        chapter_xpath = f"/html/body/div[1]/div/div/div/div[2]/div/div[2]/div[1]/div[1]/div/div[3]/div[{relative_num}]"
        # 将章节号和xpath添加到列表中
        chapter_xpaths.append((num, chapter_xpath))

    # 返回组按钮xpath列表、章节xpath列表、组数量、总章节数、最后一组章节数
    return chapter_num_group_xpaths_list, chapter_xpaths, all_chapters_num, last_chapters_num