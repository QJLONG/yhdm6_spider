'''
Version: 3.0
Autor: hummer
Date: 2023-05-04 10:25:49
LastEditors: hummer
LastEditTime: 2023-05-09 16:05:10
'''

import requests
import aiohttp
import asyncio
import aiofiles
import re
import os
from Crypto.Cipher import AES
import shutil


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
    "referer": "https://yhdm6.top/index.php/vod/detail/id/9833.htm4",
    "cookie": "_gid=GA1.2.1594533158.1683167519; __cf_bm=jCYn7Z4RXbqGY65kf3sCCwcBCeLREJ7LCl_Uxj_3O9Q-1683167519-0-AZgGTDPkE5AaymENrlrlLBeVJ2N72S/bl8YwZ5B+7vzayUZC9ytY8OAylXmyJ7JmBK8BDcpQBYfRptRfel9BzwfkQsAupjdn3MbZ3OTsz3tR; history=%5B%7B%22name%22%3A%22%E9%95%87%E9%AD%82%E8%A1%97%E7%AC%AC%E4%BA%8C%E5%AD%A3%22%2C%22pic%22%3A%22https%3A%2F%2Fpic.feisuimg.com%2Fupload%2Fvod%2F20220725-1%2F9961b9030755e1978d78b19cd27146e0.jpg%22%2C%22link%22%3A%22%2Findex.php%2Fvod%2Fplay%2Fid%2F9833%2Fsid%2F1%2Fnid%2F1.html%22%2C%22part%22%3A%22%E7%AC%AC01%E9%9B%86%22%7D%5D; PHPSESSID=62papah3o5lpit87lo23aj6amd; _ga_JPE4Z6KP45=GS1.1.1683167518.2.1.1683167842.0.0.0; _ga_1V0B425XLD=GS1.1.1683167518.2.1.1683167842.0.0.0; _ga=GA1.2.225444624.1683078169"
}


def get_m3u8(url):
    """
    description: 获取视频的m3u8文件,并保存到当前目录
    params:
        url: 樱花动漫视频的url
    returns:
        file_name: 集数.m3u8(例如: 1.m3u8)
        domain_name: ts文件url的域名
    """
    resp = requests.get(url, headers=headers)
    # with open("test.html" ,'w') as f:
    #     f.write(resp.text)
    html = resp.text
    pattern = re.compile(r'https:\\/\\/s\d.fsvod\d.com\\/.*?/index.m3u8', re.S)
    url_m3u8 = pattern.findall(html)[0].replace("\\", "")
    print("m3u8_url:", url_m3u8)
    domain_name = re.findall("https://s\d.fsvod\d.com", url_m3u8)[0]
    print("domain:", domain_name)
    resp2 = requests.get(url_m3u8, headers=headers)
    # print(resp2.text)
    pattern2 = re.compile(r"RESOLUTION=\d+x\d+\s(.*?)$", re.S)
    url_m3u8_2 = domain_name + pattern2.findall(resp2.text)[0]
    resp_m3u8 = requests.get(url_m3u8_2, headers=headers)
    file_name = url.split("/")[-1].replace(".html", "")
    with open(file_name+".m3u8", 'w') as f:
        f.write(resp_m3u8.text)
    print(file_name+".m3u8"+"文件获取成功")
    return file_name+".m3u8", domain_name


async def aio_download_ts(session, ts_url, path):
    """
    description: 下载一个ts文件
    params:
        session: 用于下载ts文件的会话
        ts_url: ts文件的下载地址
        path: 存放ts文件的路径(1/)
    """
    if not os.path.exists(path):
        os.mkdir(path)
    try:
        ts_name = ts_url.split("/")[-1]
        async with session.get(ts_url) as resp:
            async with aiofiles.open(os.path.join(path, ts_name), mode='wb') as f:
                await f.write(await resp.content.read())
                # print(ts_name + '下载完成')
    except TimeoutError as e:         print("ts文件下载超时, 自动跳过该文件")


async def download_ts(domain_name,m3u8_path):
    """
    description: 构建ts文件下载任务
    params:
        domain_name: ts文件url的域名
        m3u8_path: m3u8文件的路径(1.m3u8)
    returns:
        None
    """
    tasks = []
    timeout = aiohttp.ClientTimeout(total=60, sock_read=30)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        with open(m3u8_path, mode='r', encoding='utf-8') as f:
            for line in f:
                if not line.startswith("/"):
                    continue
                else:
                    ts_url = domain_name + line.strip()
                    # print(ts_url)
                    tasks.append(asyncio.create_task(aio_download_ts(session, ts_url, m3u8_path.split(".")[0])))
            await asyncio.wait(tasks)
    
    print("下载完成")



async def aio_dec_ts(ts_path, temp_path, key):
    """
    description: 解密单个ts文件
    params:
        ts_path: ts文件的路径(1/xxx.ts)
        temp_path: ts解密后存放的路径
        key: 解密的密钥
    returns:
        None
    """
    # temp_path = 'dec_temp/'
    if not os.path.exists(temp_path):
        os.mkdir(temp_path)
    aes = AES.new(key=key, mode=AES.MODE_CBC, IV=b'0000000000000000')

    try:
        async with aiofiles.open(ts_path, mode='rb') as f1:
            async with aiofiles.open(temp_path + ts_path.split("/")[-1], mode='wb') as f2:
                bs = await f1.read()
                await f2.write(aes.decrypt(bs))
                # print("处理完毕")
    except FileNotFoundError as e:
        print("文件未找到", ts_path)



async def dec_ts(m3u8_path, path, domain_name):
    """
    description: 创建任务解密ts文件
    params:
        domain_name: ts文件url的域名
        m3u8_path: m3u8文件的路径(1.m3u8)
        path: ts文件所在的路径(1/)
    returns:
        None
    """
    tasks = []
    with open(m3u8_path, mode='r', encoding='utf-8') as f:
        text = f.read()
        key_url = domain_name + re.findall(r'URI="(.*?)"', text)
        if key_url:
            key_url = key_url[0]
        else:
            print("不需要解密")
            return
        resp = requests.get(key_url)
        key = resp.content
        print("key:", key)
    async with aiofiles.open(m3u8_path, mode='r', encoding='utf-8') as f:
        async for line in f:
            if not line.startswith("/"):
                continue
            else:
                ts_path = path + line.strip().split("/")[-1]
                tasks.append(asyncio.create_task(aio_dec_ts(ts_path,temp_path="dec_"+path ,key=key)))
        await asyncio.wait(tasks)
    print("解密完成")
    shutil.rmtree(path)
    



def merge_ts(m3u8_path="1.m3u8", ts_path="dec_temp", file_name="test.mp4"):
    ts_names = []
    with open(m3u8_path, mode='r', encoding='utf-8') as f:
        for line in f:
            if not line.startswith("/"):
                continue
            else:
                line = line.strip()                 
                ts_name = os.path.join(ts_path, line.split("/")[-1])
                if not os.path.exists(ts_name):
                    continue
                ts_names.append(ts_name)
    cmd = f"copy /b {ts_names[0]}+{ts_names[1]} {file_name}"
    os.system(cmd)
    os.system("dir")
    for ts_name in ts_names[2:]:
        cmd = f"copy /b {file_name}+{ts_name} {file_name}"
        os.system(cmd)
    print("合并完成")
    shutil.rmtree(ts_path)

                    

def main():
    url="https://yhdm6.top/index.php/vod/play/id/16102/sid/2/nid/1.html"
    m3u8_path, domain_name = get_m3u8(url)
    loop1 = asyncio.get_event_loop()
    loop1.run_until_complete(download_ts(domain_name,m3u8_path))
    with open(m3u8_path, mode='r', encoding='utf-8') as f:
        text = f.read()
        key_url = re.findall(r'URI="(.*?)"', text)
        if not key_url:
            merge_ts(m3u8_path, m3u8_path.split(".")[0], m3u8_path.split(".")[0]+".mp4")
        else:
            key_url = domain_name + key_url[0]
            loop2 = asyncio.get_event_loop()
            loop2.run_until_complete(dec_ts(m3u8_path, m3u8_path.split(".")[0]+'/', domain_name))
            merge_ts(m3u8_path, ts_path='dec_'+m3u8_path.split(".")[0], file_name=m3u8_path.split(".")[0]+".mp4") # dec_1
    os.remove(m3u8_path)

    
if __name__ == '__main__':
    main()
    # for i in range(1,7):
    #     url = f"https://yhdm6.top/index.php/vod/play/id/17065/sid/5/nid/{i}.html"
    #     main(url)

