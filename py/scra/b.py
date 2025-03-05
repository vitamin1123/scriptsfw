import requests
from lxml import etree
import time
import os
import random
import json
import re

a = [

]

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'cache-control': 'max-age=0',
    'if-modified-since': 'Wed, 12 Feb 2025 13:42:30 GMT',
    'priority': 'u=0, i',
    'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Microsoft Edge";v="132"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0',
}

# response = requests.get('https://cnjp.xyz/', headers=headers)

def extract_vod_list(script_content):
    # 使用正则表达式提取 JSON 字符串（包括 .replace 部分）
    match = re.search(r'const vod_list = JSON\.parse\(\'(.+?)\'\)\.replace\(/\\\\/g, "\\\\\\\\"\)', script_content)
    if not match:
        raise ValueError("未找到 vod_list 的 JSON 数据")

    # 获取 JSON 字符串
    json_str = match.group(1)

    # 替换转义字符（例如 \\u 和 \\/）
    json_str = json_str.replace('\\/', '/').replace('\\\\', '\\')

    # 解析 JSON 字符串为 Python 对象
    vod_list = json.loads(json_str)
    print(vod_list)
    return vod_list

def get_cnt(url):
    response = requests.get(url,headers=headers)
    html_element = etree.HTML(response.content)
    res = html_element.xpath('/html/body/div[2]/div[3]//ul/li[last()]/a/text()')[0]
    print(res)
    return res

def get_each_page(url):                                      
    response = requests.get(url,headers=headers)
    html_element = etree.HTML(response.content)
    script_element = html_element.xpath('/html/body/script[1]')
    if script_element:  # 检查是否找到了 script 标签
        script_content = script_element[0].text  # 获取 script 标签的内容
        print('Script content:', extract_vod_list(script_content))
    else:
        print('未找到 script 标签')



if __name__ == '__main__':
    for i in a:
        pages = get_cnt(i)
        print(pages)
        #for j in range(1,int(pages)+1):
        for j in range(1,2):
            new_url = i+str(j)
            print(new_url)
            get_each_page(new_url)
            time.sleep(1)