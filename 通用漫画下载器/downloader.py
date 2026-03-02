import os
import asyncio
import aiohttp
import aiofiles
import time
import json
import requests
from concurrent.futures import ThreadPoolExecutor


async def download_with_aiohttp(url, file_path, timeout=10):
    """使用aiohttp下载"""
    try:
        connector = aiohttp.TCPConnector(
            limit=1,
            enable_cleanup_closed=True,
            force_close=True,
            ssl=False
        )
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as session:
            async with session.get(url, allow_redirects=True) as response:
                if response.status == 200:
                    content = await response.read()
                    if len(content) > 1024:
                        async with aiofiles.open(file_path, 'wb') as f:
                            await f.write(content)
                        return True, len(content)
                    else:
                        return False, f"内容过小({len(content)}字节)"
                else:
                    return False, f"状态码{response.status}"
    except asyncio.TimeoutError:
        return False, "超时"
    except Exception as e:
        return False, str(e)[:50]


def download_with_requests(url, file_path, timeout=10):
    """使用requests下载（同步）"""
    try:
        response = requests.get(url, stream=True, timeout=timeout)
        response.raise_for_status()
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        
        if os.path.getsize(file_path) > 1024:
            return True, os.path.getsize(file_path)
        else:
            return False, "内容过小"
    except Exception as e:
        return False, str(e)[:50]


async def download_image(url, index, folder_name, chapter_num, progress_callback=None):
    """
    下载单张图片
    先用aiohttp，失败再用requests
    """
    file_path = os.path.join(folder_name, f"{index}.jpg")
    
    success, info = await download_with_aiohttp(url, file_path)
    if success:
        print(f"  ✓ 第{index}张图片下载成功(aiohttp)")
        if progress_callback:
            progress_callback(info)
        return None
    
    print(f"  → 第{index}张aiohttp失败({info})，尝试requests...")
    
    loop = asyncio.get_event_loop()
    success, info = await loop.run_in_executor(
        None,
        download_with_requests,
        url,
        file_path,
        10
    )
    
    if success:
        print(f"  ✓ 第{index}张图片下载成功(requests)")
        if progress_callback:
            progress_callback(info)
        return None
    else:
        print(f"  ✗ 第{index}张图片最终失败: {info}")
        print(f"    URL: {url}")
        if progress_callback:
            progress_callback(0)
        return {
            'url': url,
            'chapter_num': chapter_num,
            'image_index': index,
            'folder': folder_name,
            'path': file_path,
            'error': info
        }


async def download_batch_coroutine(images_to_download, concurrent_limit, progress_callback=None):
    """
    协程模式批量下载图片，控制并发数
    images_to_download: [(url, index, folder_name, chapter_num), ...]
    """
    semaphore = asyncio.Semaphore(concurrent_limit)
    failed_list = []

    async def download_with_semaphore(url, index, folder_name, chapter_num):
        async with semaphore:
            result = await download_image(url, index, folder_name, chapter_num, progress_callback)
            if result:
                failed_list.append(result)
            await asyncio.sleep(0.3)

    tasks = [
        download_with_semaphore(url, index, folder, chapter_num)
        for url, index, folder, chapter_num in images_to_download
    ]

    await asyncio.gather(*tasks)
    return failed_list


def download_batch_thread_coroutine(images_to_download, concurrent_limit, thread_count=4, progress_callback=None):
    """
    多线程+协程模式批量下载图片
    线程数控制章节级并发，协程控制图片级并发
    images_to_download: [(url, index, folder_name, chapter_num), ...]
    """
    def process_chunk(chunk):
        """在线程中运行协程下载"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                download_batch_coroutine(chunk, concurrent_limit, progress_callback)
            )
            return result
        finally:
            loop.close()

    # 将图片分成thread_count个块
    chunk_size = max(1, len(images_to_download) // thread_count)
    chunks = []
    for i in range(thread_count):
        start = i * chunk_size
        end = (i + 1) * chunk_size if i < thread_count - 1 else len(images_to_download)
        chunks.append(images_to_download[start:end])

    failed_list = []
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        results = executor.map(process_chunk, chunks)
        for result in results:
            failed_list.extend(result)

    return failed_list


async def download_batch(images_to_download, concurrent_limit, thread_count=4, use_thread_coroutine=True, progress_callback=None):
    """
    批量下载图片，可选择使用纯协程或多线程+协程
    """
    if use_thread_coroutine and thread_count > 1:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            download_batch_thread_coroutine,
            images_to_download,
            concurrent_limit,
            thread_count,
            progress_callback
        )
    else:
        return await download_batch_coroutine(images_to_download, concurrent_limit, progress_callback)


async def download_chapter_images(herf_list, folder_name, chapter_num, concurrent_limit=3, thread_count=4, use_thread_coroutine=True, progress_callback=None):
    """下载单个章节的图片"""
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    print(f"\n[章节{chapter_num}] 开始下载 {len(herf_list)} 张图片...")
    start_time = time.time()

    images_to_download = [(url, i, folder_name, chapter_num) for i, url in enumerate(herf_list, 1)]
    failed = await download_batch(images_to_download, concurrent_limit, thread_count, use_thread_coroutine, progress_callback)

    elapsed = time.time() - start_time
    print(f"[章节{chapter_num}] 完成，耗时{elapsed:.1f}秒，失败{len(failed)}张")

    return failed


def check_missing_images(herf_list, folder_name, chapter_num):
    """检查哪些图片缺失或损坏"""
    missing = []
    for i, url in enumerate(herf_list, 1):
        file_path = os.path.join(folder_name, f"{i}.jpg")
        if not os.path.exists(file_path):
            missing.append({
                'url': url,
                'chapter_num': chapter_num,
                'image_index': i,
                'folder': folder_name,
                'path': file_path,
                'error': '文件不存在'
            })
        elif os.path.getsize(file_path) < 1024:
            missing.append({
                'url': url,
                'chapter_num': chapter_num,
                'image_index': i,
                'folder': folder_name,
                'path': file_path,
                'error': '文件过小(可能损坏)'
            })
    return missing


def save_image_urls_to_json(all_chapters_data, comic_name, base_path=None):
    """保存图片URL映射到JSON文件"""
    if base_path is None:
        base_path = os.getcwd()
    
    main_folder = os.path.join(base_path, comic_name)
    
    url_mapping = {
        "comic_name": comic_name,
        "base_path": main_folder,
        "total_chapters": len(all_chapters_data),
        "chapters": []
    }
    
    for chapter_data in all_chapters_data:
        chapter_num = chapter_data['chapter_num']
        herf_list = chapter_data['herf_list']
        
        chapter_info = {
            "chapter_num": chapter_num,
            "folder_name": str(chapter_num),
            "total_images": len(herf_list),
            "images": []
        }
        
        for i, url in enumerate(herf_list, 1):
            chapter_info["images"].append({
                "index": i,
                "filename": f"{i}.jpg",
                "url": url
            })
        
        url_mapping["chapters"].append(chapter_info)
    
    json_path = os.path.join(main_folder, "image_urls.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(url_mapping, f, ensure_ascii=False, indent=2)
    
    print(f"\n图片URL映射已保存到: {json_path}")
    return json_path


async def download_all_chapters(all_chapters_data, comic_name, base_path=None, save_json_only=False, concurrent_limit=3, download_thread_count=4, use_thread_coroutine=True, progress_callback=None, max_retries=3):
    """下载所有章节，可选只保存JSON不下载
    
    Args:
        max_retries: 失败后重试次数，默认3次
    
    Returns:
        tuple: (failed_list, failed_json_path, should_zip)
            - failed_list: 失败的图片列表（空列表表示全部成功）
            - failed_json_path: 失败JSON的保存路径（全部成功时返回None）
            - should_zip: 是否应该压缩文件（有失败图片时返回False）
    """
    print(f"\n{'='*50}")
    print(f"开始处理漫画: {comic_name}")
    print(f"{'='*50}")
    
    if base_path is None:
        base_path = os.getcwd()

    main_folder = os.path.join(base_path, comic_name)
    if not os.path.exists(main_folder):
        os.makedirs(main_folder)
    
    json_path = save_image_urls_to_json(all_chapters_data, comic_name, base_path)
    
    if save_json_only:
        print(f"仅保存JSON，跳过下载")
        return [], None, True
    
    total_start = time.time()
    all_failed = []

    for chapter_data in all_chapters_data:
        chapter_num = chapter_data['chapter_num']
        herf_list = chapter_data['herf_list']

        if not herf_list:
            print(f"[章节{chapter_num}] 无图片链接，跳过")
            continue
        
        folder_name = os.path.join(main_folder, str(chapter_num))
        failed = await download_chapter_images(herf_list, folder_name, chapter_num, concurrent_limit, download_thread_count, use_thread_coroutine, progress_callback)
        all_failed.extend(failed)

    total_elapsed = time.time() - total_start
    print(f"\n{'='*50}")
    print(f"首次下载完成！总耗时: {total_elapsed:.1f}秒")
    print(f"失败: {len(all_failed)} 张")
    
    # 重试失败图片
    if all_failed:
        print(f"\n开始重试失败图片，共{max_retries}轮...")
        for retry_round in range(1, max_retries + 1):
            if not all_failed:
                break
            
            print(f"\n{'='*50}")
            print(f"第 {retry_round}/{max_retries} 轮重试")
            print(f"{'='*50}")
            
            # 准备重试的图片列表
            images_to_retry = [
                (img['url'], img['image_index'], img['folder'], img['chapter_num'])
                for img in all_failed
            ]
            
            # 使用多线程+协程重试
            still_failed = await download_batch(
                images_to_retry, 
                concurrent_limit, 
                download_thread_count, 
                use_thread_coroutine, 
                progress_callback
            )
            
            success_count = len(all_failed) - len(still_failed)
            print(f"\n第 {retry_round} 轮重试完成: 成功 {success_count} 张，仍然失败 {len(still_failed)} 张")
            all_failed = still_failed
    
    # 保存失败列表到JSON
    if all_failed:
        print(f"\n失败的图片URL列表:")
        for failed in all_failed:
            print(f"  章节{failed['chapter_num']}-第{failed['image_index']}张: {failed['url']}")
        
        failed_json_path = save_failed_json(all_failed, comic_name, base_path)
        print(f"{'='*50}")
        return all_failed, failed_json_path, False  # 有失败图片，不压缩
    else:
        # 全部成功，删除JSON文件
        json_path = os.path.join(main_folder, "image_urls.json")
        if os.path.exists(json_path):
            os.remove(json_path)
            print(f"已删除image_urls.json（无缺页）")
        
        # 删除可能存在的失败列表文件
        failed_json_path = os.path.join(main_folder, "failed_images.json")
        if os.path.exists(failed_json_path):
            os.remove(failed_json_path)
            print(f"已删除failed_images.json（全部成功）")
    
    print(f"{'='*50}")
    return [], None, True  # 全部成功，可以压缩


def save_failed_json(failed_list, comic_name, base_path=None):
    """保存失败列表到JSON文件"""
    if base_path is None:
        base_path = os.getcwd()
    
    main_folder = os.path.join(base_path, comic_name)
    
    failed_data = {
        "comic_name": comic_name,
        "base_path": main_folder,
        "total_failed": len(failed_list),
        "failed_images": failed_list
    }
    
    failed_json_path = os.path.join(main_folder, "failed_images.json")
    with open(failed_json_path, 'w', encoding='utf-8') as f:
        json.dump(failed_data, f, ensure_ascii=False, indent=2)
    
    print(f"失败列表已保存到: {failed_json_path}")
    return failed_json_path


async def download_from_failed_json(json_path, concurrent_limit=3, download_thread_count=4, use_thread_coroutine=True, progress_callback=None, max_retries=3):
    """从失败的JSON文件重新下载图片
    
    Args:
        json_path: 失败列表JSON文件路径
        concurrent_limit: 协程并发数
        download_thread_count: 线程数
        use_thread_coroutine: 是否使用多线程+协程
        progress_callback: 进度回调函数
        max_retries: 失败后重试次数
    
    Returns:
        tuple: (still_failed, all_success, image_dimensions)
            - still_failed: 仍然失败的图片列表
            - all_success: 是否全部成功
            - image_dimensions: 成功下载图片的宽高信息字典 {path: (width, height)}
    """
    print(f"\n{'='*50}")
    print(f"从失败列表重新下载")
    print(f"{'='*50}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    comic_name = data['comic_name']
    base_path = data['base_path']
    failed_images = data['failed_images']
    
    print(f"漫画名称: {comic_name}")
    print(f"基础路径: {base_path}")
    print(f"待重试: {len(failed_images)} 张")
    
    if not failed_images:
        print("没有需要重试的图片")
        return [], True, {}
    
    images_to_download = [
        (img['url'], img['image_index'], img['folder'], img['chapter_num'])
        for img in failed_images
    ]
    
    all_failed = []
    image_dimensions = {}  # 记录图片宽高
    
    # 首次下载
    start_time = time.time()
    all_failed = await download_batch(images_to_download, concurrent_limit, download_thread_count, use_thread_coroutine, progress_callback)
    
    # 获取成功下载图片的宽高
    from PIL import Image
    for img in failed_images:
        file_path = img['path']
        if os.path.exists(file_path) and os.path.getsize(file_path) > 1024:
            try:
                with Image.open(file_path) as im:
                    image_dimensions[file_path] = (im.width, im.height)
            except Exception as e:
                print(f"  无法获取图片尺寸 {file_path}: {e}")
    
    # 重试机制
    if all_failed and max_retries > 0:
        print(f"\n开始重试，共{max_retries}轮...")
        for retry_round in range(1, max_retries + 1):
            if not all_failed:
                break
            
            print(f"\n{'='*50}")
            print(f"第 {retry_round}/{max_retries} 轮重试")
            print(f"{'='*50}")
            
            images_to_retry = [
                (img['url'], img['image_index'], img['folder'], img['chapter_num'])
                for img in all_failed
            ]
            
            still_failed = await download_batch(images_to_retry, concurrent_limit, download_thread_count, use_thread_coroutine, progress_callback)
            
            # 获取新成功图片的宽高
            for img in all_failed:
                file_path = img['path']
                if os.path.exists(file_path) and os.path.getsize(file_path) > 1024:
                    if file_path not in image_dimensions:
                        try:
                            with Image.open(file_path) as im:
                                image_dimensions[file_path] = (im.width, im.height)
                        except Exception as e:
                            print(f"  无法获取图片尺寸 {file_path}: {e}")
            
            success_count = len(all_failed) - len(still_failed)
            print(f"\n第 {retry_round} 轮重试完成: 成功 {success_count} 张，仍然失败 {len(still_failed)} 张")
            all_failed = still_failed
    
    elapsed = time.time() - start_time
    
    print(f"\n{'='*50}")
    print(f"重试完成！耗时: {elapsed:.1f}秒")
    print(f"成功: {len(failed_images) - len(all_failed)} 张")
    print(f"仍然失败: {len(all_failed)} 张")
    
    if all_failed:
        print(f"\n仍然失败的图片:")
        for failed in all_failed:
            print(f"  章节{failed['chapter_num']}-第{failed['image_index']}张: {failed['url']}")
        
        # 保存更新后的失败列表
        failed_json_path = save_failed_json(all_failed, comic_name, base_path)
        print(f"\n更新后的失败列表已保存到: {failed_json_path}")
        
        # 保存图片宽高信息
        if image_dimensions:
            dimensions_json_path = os.path.join(base_path, "image_dimensions.json")
            dimensions_data = {
                "comic_name": comic_name,
                "base_path": base_path,
                "total_images": len(image_dimensions),
                "dimensions": {}
            }
            for path, (width, height) in image_dimensions.items():
                # 将绝对路径转换为相对路径
                rel_path = os.path.relpath(path, base_path)
                dimensions_data["dimensions"][rel_path] = {
                    "width": width,
                    "height": height,
                    "path": path
                }
            with open(dimensions_json_path, 'w', encoding='utf-8') as f:
                json.dump(dimensions_data, f, ensure_ascii=False, indent=2)
            print(f"图片宽高信息已保存到: {dimensions_json_path}")
        
        print(f"{'='*50}")
        return all_failed, False, image_dimensions
    else:
        # 全部成功，删除失败列表文件
        if os.path.exists(json_path):
            os.remove(json_path)
            print(f"\n全部下载成功，已删除失败列表: {json_path}")
        
        # 保存图片宽高信息
        if image_dimensions:
            dimensions_json_path = os.path.join(base_path, "image_dimensions.json")
            dimensions_data = {
                "comic_name": comic_name,
                "base_path": base_path,
                "total_images": len(image_dimensions),
                "dimensions": {}
            }
            for path, (width, height) in image_dimensions.items():
                # 将绝对路径转换为相对路径
                rel_path = os.path.relpath(path, base_path)
                dimensions_data["dimensions"][rel_path] = {
                    "width": width,
                    "height": height,
                    "path": path
                }
            with open(dimensions_json_path, 'w', encoding='utf-8') as f:
                json.dump(dimensions_data, f, ensure_ascii=False, indent=2)
            print(f"图片宽高信息已保存到: {dimensions_json_path}")
    
    print(f"{'='*50}")
    return [], True, image_dimensions


async def download_cover_image(url, comic_name, base_path=None):
    """下载封面图片"""
    if base_path is None:
        base_path = os.getcwd()

    main_folder = os.path.join(base_path, comic_name)
    folder_name = os.path.join(main_folder, "0")

    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    print(f"\n开始下载封面...")
    file_path = os.path.join(folder_name, "cover.jpg")
    
    success, info = await download_with_aiohttp(url, file_path)
    if not success:
        loop = asyncio.get_event_loop()
        success, info = await loop.run_in_executor(None, download_with_requests, url, file_path, 10)
    
    if success:
        print("封面下载成功")
        return True
    else:
        print(f"封面下载失败: {info}")
        print(f"URL: {url}")
        return False
