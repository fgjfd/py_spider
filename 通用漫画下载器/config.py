import os

BROWSER_PATHS = {
    'edge': r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    'chrome': r"C:\Program Files\Google\Chrome\Application\chrome.exe"
}

DEFAULT_SITE = '御漫画'

SITES = {
    '御漫画': {
        'site_url': 'http://m.yumanhua.com/',
        'xpaths': {
            'search_button': '/html/body/header/div/div[2]/img[1]',
            'search_input': '/html/body/div[3]/div[6]/div[1]/div/div[1]/div/input',
            'search_submit': '/html/body/div[3]/div[6]/div[1]/div/div[1]/button',
            'search_result': '/html/body/div[3]/div[6]/div[1]/div/div[2]/div/ul/li/a/div[1]/img',
            'cover_image': '/html/body/div[2]/div[1]/div/div[1]/div/img',
            'show_more_button': '/html/body/div[2]/div[3]/div[2]/div/button',
            'chapter_list': '/html/body/div[2]/div[3]/div[2]/ul/li',
            'chapter_link': './a',
            'image_list': '/html/body/div[2]/div[2]/div',
            'image_item': '/html/body/div[2]/div[2]/div[num]/img'
        },
        'image_attr': 'data-src',
        'chapter_group_size': None
    },
    '快看': {
        'site_url': 'https://www.kuaikanmanhua.com/',
        'xpaths': {
            'search_input': '/html/body/div[1]/div/div/div/div[1]/div[2]/div/div[1]/input',
            'search_button': '/html/body/div[1]/div/div/div/div[1]/div[2]/div/div[1]/a',
            'search_result': '/html/body/div[1]/div/div/div/div[3]/div[1]/div[1]/div[1]/a',
            'cover_image': '/html/body/div[1]/div/div/div/div[2]/div/div[1]/div/div[1]/img[3]',
            'chapter_list': '/html/body/div[1]/div/div/div/div[2]/div/div[2]/div[1]/div[1]/div/div[3]/div',
            'chapter_group_button': '/html/body/div[1]/div/div/div/div[2]/div/div[2]/div[1]/div[1]/div/div[2]/div',
            'chapter_image_parent': '/html/body/div[1]/div/div/div/div[4]/div[1]/div[1]/div',
            'chapter_image': '/html/body/div[1]/div/div/div/div[4]/div[1]/div[1]/div[num]/img'
        },
        'image_attr': 'data-src',
        'chapter_group_size': 50
    },
    '好多漫': {
        'site_url': 'https://www.haoduoman.com/',
        'xpaths': {
            'search_input': '/html/body/header/div[2]/div/div[2]/div/form/div/p[1]/input',
            'search_button': '/html/body/header/div[2]/div/div[2]/div/form/div/p[2]/button',
            'search_result': '/html/body/main/div/div[2]/div/div[1]/div/div/div[2]/a',
            'cover_image': '/html/body/main/div/div[2]/div[1]/div/div/div/div[1]/img',
            'chapter_list': '/html/body/main/div/div[3]/div[2]/ul/li',
            'chapter_link': '/html/body/main/div/div[3]/div[2]/ul/li[num]/a',
            'chapter_image_parent': '/html/body/main/div[1]/div/div[1]/div',
            'chapter_image_data_original': '/html/body/main/div[1]/div/div[1]/div[num]'
        },
        'image_attr': 'data-original',
        'chapter_group_size': None
    }
}
