import configparser
import csv
import json
import os
import re
import lxml
import time
import threading
import queue
import requests
from bs4 import BeautifulSoup
from common import readconfig

HUANQIU = 'https://world.huanqiu.com/article/'
HUANQIU_OFFSET = 20
HISTORY = "./config/history.json"
STOP = False
HEADER = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36 Edg/88.0.705.81",
    "Cookie": '''UM_distinctid=177f21c29bf10d-043ddbd82b4eef-7a667166-144000-177f21c29c039b; _ma_tk=hewd6oh2rs0o2mqybcrd3s60un56m46w; REPORT_UID_=cJ869QdbSP132oZ6591juDJYZZ8wK0SC; Hm_lvt_1fc983b4c305d209e7e05d96e713939f=1614674668,1614738118,1614738291,1614908983; CNZZDATA1000010102=1231572127-1614671036-https%253A%252F%252Fwww.huanqiu.com%252F%7C1614914069; Hm_lpvt_1fc983b4c305d209e7e05d96e713939f=1614914406'''
}


class ParserNewsList:
    def __init__(self, url_queue, lock, news_info_fp):
        super().__init__()
        self.url_queue = url_queue
        self.stop_flag = False
        self.lock = lock
        self.news_info_fp = news_info_fp

    def run(self):
        global world_base_url
        global world_article_base_url
        global offset
        global history_json

        page = 0
        count = 0
        while not self.stop_flag:
            try:
                page_url = world_base_url.format(offset * page)
                page += 1
                res = requests.get(page_url, headers=HEADER)

                if res.content:
                    news_list = res.json().get('list')
                    news_list.pop(-1)
                    for news in news_list:
                        ctime = int(news.get("ctime"))  # 13位时间戳
                        if ctime > history_json["huanqiu_world_last_time"]:  # 筛选关键词
                            # self.data_queue.put(news)
                            aid = news.get('aid')  # aid是新闻的保存名，HUANQIU + aid为具体某条新闻的url
                            full_url = world_article_base_url + str(aid)  # 每条新闻的完整url
                            url_queue.put({"ctime": ctime, "url": full_url})
                            with lock:
                                self.news_info_fp.write(json.dumps(news, indent=4, sort_keys=True))
                                self.news_info_fp.write(",")
                            count += 1
                            print("ParserNewsList {}:{}".format(count, full_url))

                        elif ctime <= history_json["huanqiu_world_last_time"]:
                            history_json["huanqiu_world_last_time"] = ctime
                            self.stop_flag = True
                            break
                        else:
                            continue
            except:
                print('error')


class CrawlerUrlThread(threading.Thread):
    def __init__(self, name, url_queue, res_queue):
        super().__init__(name=name)
        self.url_queue = url_queue
        self.res_queue = res_queue

    def run(self):
        while not self.url_queue.empty():
            try:
                item = url_queue.get(block=False)
                ctime = item["ctime"]
                url = item["url"]
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36'
                }
                res = requests.get(url, headers=headers)
                res_queue.put({"ctime": ctime, "res": res})
                print("CrawlerUrlThread-{}: {}".format(self.name, url))
            except:
                pass


class ParserNewsThread(threading.Thread):
    def __init__(self, name, res_queue, lock, news_content_fp):
        super().__init__(name=name)
        self.res_queue = res_queue
        self.lock = lock
        self.news_content_fp = news_content_fp

    def run(self):
        while parse_exit_flag:
            try:
                item = res_queue.get(block=False)
                ctime = item["ctime"]
                res = item["res"]
                content = self.parse_response(res)
                with lock:
                    self.news_content_fp.write(
                        json.dumps({"ctime": ctime, "content": content}, indent=4, sort_keys=True))
                    self.news_content_fp.write(",")
                print("ParserNewsThread-{}: {}".format(self.name, ctime))
            except:
                pass

    def parse_response(self, res):
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'lxml')

        # 获取新闻发布时间和来源
        # reg_source = soup.select('div.metadata-info')
        # str_source = re.findall('<a href=".*">(.*)</a>', str(reg_source), re.S)
        # news_source.append(str_source)
        # str_time = re.findall('<p class="time">(.*)</p>', str(reg_source), re.S)
        # news_time.append(str_time)

        # 获取新闻内容
        reg_content = soup.select('.l-con.clear')
        str_data = re.findall('<p>(.*?)</p>', str(reg_content), re.S)  # re.S参数，多行匹配
        str_data = ''.join(str_data)  # 将data中的数组拼成一个字符串
        # 剔除<i>标签中的内容
        pat_str1 = '<i class="pic-con">.*</i>'
        pat_str2 = '<em data-scene="strong">.*</em>'  # 剔除：<em data-scene="strong">海外网3月5日电</em>
        str_data = re.sub(pat_str1, '', str_data)
        str_data = re.sub(pat_str2, '', str_data)
        return str_data


#
# class WriterThread(threading.Thread):
#     def __init__(self, name, res_queue, news_queue):
#         super().__init__(name=name)
#         self.res_queue = res_queue
#         self.news_queue = news_queue
#
#     def run(self):
#         while True:


def load_ini():
    global world_base_url
    global world_article_base_url
    global offset
    global history_json
    global crawler_threads_num
    global parser_threads_num
    global news_info_store
    global news_content_store
    global history_path


    rc = readconfig.ReadConfig()

    history_path = os.path.join(os.getcwd(), rc.cf.get("Global", "history"))

    with open(history_path) as history_json_file:
        history_json = json.load(history_json_file)
    world_base_url = rc.cf.get("Huanqiu-news", "world_base_url")
    world_article_base_url = rc.cf.get("Huanqiu-news", "world_article_base_url")
    offset = rc.cf.getint("Huanqiu-news", "offset")

    news_info_store = os.path.join(os.getcwd(),
                                   rc.cf.get("Huanqiu-news", "news_info_store"))
    news_content_store = os.path.join(os.getcwd(),
                                      rc.cf.get("Huanqiu-news", "news_content_store"))

    crawler_threads_num = rc.cf.getint("Thread", "crawler_url_threads_num")
    parser_threads_num = rc.cf.getint("Thread", "parse_news_threads_num")


if __name__ == '__main__':
    global world_base_url
    global world_article_base_url
    global offset
    global history_json
    global crawler_threads_num
    global parser_threads_num
    global news_info_store
    global news_content_store
    global history_path

    parse_exit_flag = True

    load_ini()

    lock = threading.Lock()
    news_info_fp = open(news_info_store, 'w+', encoding="utf-8")
    news_content_fp = open(news_content_store, 'w+', encoding="utf-8")

    news_info_fp.write("[")
    news_content_fp.write("[")

    url_queue = queue.Queue()
    res_queue = queue.Queue()

    producer = ParserNewsList(url_queue, lock, news_info_fp)
    producer.run()

    crawler_url_threads = []
    for i_c in range(crawler_threads_num):
        thread = CrawlerUrlThread(f"crawler-url-thread-{i_c}", url_queue, res_queue)
        crawler_url_threads.append(thread)

    parser_news_threads = []
    for i_p in range(parser_threads_num):
        thread = ParserNewsThread(f'parse-news-thread-{i_p}', res_queue, lock, news_content_fp)
        parser_news_threads.append(thread)

    for thread in crawler_url_threads:
        thread.start()

    for thread in parser_news_threads:
        thread.start()

    while not url_queue.empty():
        pass

    for thread in crawler_url_threads:
        thread.join()

    while not res_queue.empty():
        pass

    parse_exit_flag = False

    for thread in parser_news_threads:
        thread.join()

    news_info_fp.write("{}]")
    news_content_fp.write("{}]")
    news_info_fp.close()
    news_content_fp.close()
    with open(history_path) as history_json_file:
        json.dumps(history_json, indent=4, sort_keys=True)

# def keyword_filter(keywords, title):
#     if len(keywords) > 0:
#         for keyword in keywords:
#             if keyword not in title:
#                 return False
#     return True
#
#
# def time_stamp_for_13(ctime):
#     time_stamp = float(ctime / 1000)  # 13位时间戳转换为10位
#     time_array = time.localtime(time_stamp)
#     other_style_time = time.strftime("%Y-%m-%d %H:%M:%S", time_array)
#     return other_style_time
#
#
# def getTimeStamp(time_str):
#     ts = int(time.mktime(time.strptime(time_str, "%Y-%m-%d %H:%M:%S")))
#     return ts
#
#
# def assemble(news_list, news_content):
#     full_info = []
#     num = len(news_list)
#     for i in range(num):
#         one_in_list = news_list[i]
#         one_in_list.append(news_content[i])
#         full_info.append(one_in_list)
#     return full_info
#
#
# def write_one_in_csv(save_path, is_multiple, dates, titles, sources, contents, links):
#     with open(save_path, "a+", encoding='utf-8', newline='') as csv_file:
#         writer = csv.writer(csv_file)
#         writer.writerow(["date", "title", "source", "content", "link"])
#         if is_multiple:
#             for i in range(len(dates)):
#                 writer.writerow([dates[i], titles[i], sources[i], contents[i], links[i]])
#         else:
#             writer.writerow()
#
#
# def write_all_in_csv(save_path, all_info):
#     with open(save_path, "a+", encoding='utf-8', newline='') as csv_file:
#         writer = csv.writer(csv_file)
#         writer.writerow(["date", "title", "source", "link", "content"])
#         for item in all_info:
#             writer.writerow(item)
