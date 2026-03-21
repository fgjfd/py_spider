import os

BROWSER_PATHS = {
    'edge': r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    'chrome': r"C:\Program Files\Google\Chrome\Application\chrome.exe"
}

DEFAULT_SITE = '拷贝漫画'

SITES = {
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
    },
    '拷贝漫画': {
        'site_url': 'https://www.mangacopy.com/comics',
        'xpaths': {
            'search_input': '/html/body/header/div/div/div[8]/div/div/div/div/input',
            'search_button': '/html/body/header/div/div/div[8]/div/div/div/div/div',
            'search_result': '/html/body/main/div[2]/div/div/div[1]/div[1]/div[1]/a',
            'cover_image': '/html/body/main/div[1]/div/div[1]/div/img',
            'chapter_list': '/html/body/main/div[2]/div[3]/div/div[2]/div/div[1]/ul[1]/a',
            'chapter_link': '/html/body/main/div[2]/div[3]/div/div[2]/div/div[1]/ul[1]/a[num]',
            'chapter_image_parent': '/html/body/div[2]/div/ul/li',
            'chapter_image': '/html/body/div[2]/div/ul/li[num]/img'
        },
        'image_attr': 'data-src',
        'chapter_group_size': None
    },
    '腾讯动漫': {
        'site_url': 'https://ac.qq.com/',
        'xpaths': {
            'search_input': '/html/body/div[2]/div[2]/div[1]/div/div[2]/div/div[1]/input',
            'search_button': '/html/body/div[2]/div[2]/div[1]/div/div[2]/div/button',
            'search_result': '/html/body/div[3]/ul/li[1]/a',
            'cover_image': '/html/body/div[3]/div[3]/div/div/div[1]/a/img',
            'chapter_list_container': '/html/body/div[3]/em/div[2]/div[2]/div/div[2]/ol[1]/li',
            'chapter_image_parent': '/html/body/div[5]/ul/li',
            'chapter_image': '/html/body/div[5]/ul/li[num]/img'
        },
        'image_attr': 'src',
        'chapter_group_size': None
    }
}
