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
from dbConnection import MySqlConn
from bs4 import BeautifulSoup
from common import readconfig
import tools

# HUANQIU = 'https://world.huanqiu.com/article/'
# HUANQIU_OFFSET = 20
# HISTORY = "./config/history.json"
# STOP = False
HEADER = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36 Edg/88.0.705.81",
    "Cookie": '''UM_distinctid=177f21c29bf10d-043ddbd82b4eef-7a667166-144000-177f21c29c039b; _ma_tk=hewd6oh2rs0o2mqybcrd3s60un56m46w; REPORT_UID_=cJ869QdbSP132oZ6591juDJYZZ8wK0SC; Hm_lvt_1fc983b4c305d209e7e05d96e713939f=1614674668,1614738118,1614738291,1614908983; CNZZDATA1000010102=1231572127-1614671036-https%253A%252F%252Fwww.huanqiu.com%252F%7C1614914069; Hm_lpvt_1fc983b4c305d209e7e05d96e713939f=1614914406'''
}


class ParserNewsinfoThread(threading.Thread):
    def __init__(self, name, url_queue, news_info_fp):
        super().__init__(name=name)
        self.url_queue = url_queue
        self.news_info_fp = news_info_fp

    def run(self):
        global page
        global world_base_url
        global world_article_base_url
        global offset
        global history_json
        global page_lock
        global news_info_fp_lock
        global stop_flag_lock
        global stop_flag

        print("parserNewsInfoThread {} start".format(self.name))
        while not stop_flag:
            try:
                with page_lock:
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
                            title = news.get("title")
                            summary = news.get("summary")
                            aid = news.get('aid')  # aid是新闻的保存名，HUANQIU + aid为具体某条新闻的url
                            full_url = world_article_base_url + str(aid)  # 每条新闻的完整url
                            url_queue.put({"ctime": ctime, "title": title, "summary": summary, "url": full_url})

                            news_info_fp_lock.acquire(timeout=1)
                            self.news_info_fp.write(json.dumps(news, indent=4, sort_keys=True))
                            self.news_info_fp.write(",")
                            news_info_fp_lock.release()

                            print("ParserNewsList:{}".format(self.name))

                        else:
                            with stop_flag_lock:
                                stop_flag = True
                            break
            except:
                print('error')
        print("parserNewsInfoThread {} end".format(self.name))


class CrawlerUrlThread(threading.Thread):
    def __init__(self, name, url_queue, res_queue):
        super().__init__(name=name)
        self.url_queue = url_queue
        self.res_queue = res_queue

    def run(self):
        print("CrawlerUrlThread {} start".format(self.name))

        while crawl_url_exit_flag:
            try:
                item = url_queue.get(block=False)

                url = item["url"]
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36'
                }
                res = requests.get(url, headers=headers)
                item["res"] = res
                res_queue.put(item)
                print("CrawlerUrlThread-{}: {}".format(self.name, url))
                print(crawl_url_exit_flag)
            except queue.Empty:
                continue
            except:
                pass

        print("CrawlerUrlThread {} end".format(self.name))


class ParserNewsThread(threading.Thread):
    def __init__(self, name, res_queue, news_content_fp):
        super().__init__(name=name)
        self.res_queue = res_queue
        self.news_content_fp = news_content_fp

    def run(self):
        global news_content_fp_lock

        while parse_content_exit_flag:
            try:
                item = res_queue.get(block=False)
                ctime = item["ctime"]
                res = item["res"]
                news_detail = self.parse_response(res)
                news_detail["ctime"] = item["ctime"]
                news_detail["title"] = item["title"]
                news_detail["summary"] = item["summary"]
                news_content_fp_lock.acquire(timeout=1)
                self.news_content_fp.write(
                        json.dumps(news_detail, indent=4, sort_keys=True))
                self.news_content_fp.write(",")
                news_content_fp_lock.release()
                print("ParserNewsThread-{}: {}".format(self.name, ctime))
            except queue.Empty:
                continue
            except:
                pass

    def parse_response(self, res):
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'lxml')

        # news title
        # reg_title = soup.select("div.t-container-title")
        # str_title = re.findall("<h3>(.*)</h3>", str(reg_title), re.S)

        # 获取新闻发布时间和来源
        reg_source = soup.select('div.metadata-info')
        str_source = re.findall('<a href=".*">(.*)</a>', str(reg_source), re.S)[0]
        str_time = re.findall('<p class="time">(.*)</p>', str(reg_source), re.S)[0]

        # 获取新闻内容
        reg_content = soup.select('.l-con.clear')
        str_data = re.findall('<p>(.*?)</p>', str(reg_content), re.S)  # re.S参数，多行匹配
        str_data = ''.join(str_data)  # 将data中的数组拼成一个字符串
        # 剔除<i>标签中的内容
        pat_str1 = '<i class="pic-con">.*</i>'
        pat_str2 = '<em data-scene="strong">.*</em>'  # 剔除：<em data-scene="strong">海外网3月5日电</em>
        str_data = re.sub(pat_str1, '', str_data)
        str_data = re.sub(pat_str2, '', str_data)
        return {"source": str_source, "time": str_time, "content": str_data}


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
    global parser_newsinfo_num
    global crawler_threads_num
    global parser_threads_num
    global news_info_store
    global news_content_store
    global history_path
    global news_info_fp_lock
    global news_content_fp_lock
    global page_lock
    global crawl_url_exit_flag
    global parse_content_exit_flag
    global stop_flag_lock
    global stop_flag
    global page

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
    parser_newsinfo_num = rc.cf.getint("Thread", "parse_newsinfo_threads_num")

    page = 0

    page_lock = threading.Lock()
    news_info_fp_lock = threading.Lock()
    news_content_fp_lock = threading.Lock()
    stop_flag_lock = threading.Lock()

    parse_content_exit_flag = True
    crawl_url_exit_flag = True
    stop_flag = False


if __name__ == '__main__':
    global world_base_url
    global world_article_base_url
    global offset
    global history_json
    global crawler_threads_num
    global parser_threads_num
    global parser_newsinfo_num
    global news_info_store
    global news_content_store
    global history_path
    global page_lock
    global news_info_fp_lock
    global news_content_fp_lock
    global parse_content_exit_flag
    global crawl_url_exit_flag
    global stop_flag_lock
    global stop_flag
    global page

    load_ini()
    #
    # print("The time of latest news saved:{}\n".format(history_json["huanqiu_world_last_time"]))
    #
    start_time = time.time()

    news_info_fp = open(news_info_store, 'w+', encoding="utf-8")
    news_content_fp = open(news_content_store, 'w+', encoding="utf-8")

    news_info_fp.write("[")
    news_content_fp.write("[")

    url_queue = queue.Queue()
    res_queue = queue.Queue()

    parser_newsinfo_threads = []
    for i_p in range(parser_newsinfo_num):
        thread = ParserNewsinfoThread(f"parse-newsinfo-thread{i_p}", url_queue, news_info_fp)
        parser_newsinfo_threads.append(thread)

    crawler_url_threads = []
    for i_c in range(crawler_threads_num):
        thread = CrawlerUrlThread(f"crawler-url-thread-{i_c}", url_queue, res_queue)
        crawler_url_threads.append(thread)

    parser_news_threads = []
    for i_p in range(parser_threads_num):
        thread = ParserNewsThread(f'parse-news-thread-{i_p}', res_queue, news_content_fp)
        parser_news_threads.append(thread)

    for thread in parser_newsinfo_threads:
        thread.start()

    for thread in crawler_url_threads:
        thread.start()

    for thread in parser_news_threads:
        thread.start()

    while not stop_flag:
        pass

    for thread in parser_newsinfo_threads:
        thread.join()

    while not url_queue.empty():
        pass

    crawl_url_exit_flag = False

    for thread in crawler_url_threads:
        thread.join()

    while not res_queue.empty():
        pass

    parse_content_exit_flag = False

    for thread in parser_news_threads:
        thread.join()

    news_info_fp.write("{}]")
    news_content_fp.write("{}]")
    news_info_fp.close()
    news_content_fp.close()

    with open(history_path, "w+", encoding="utf8") as history_json_file:
        # 将第一条新闻的ctime设置为last_time
        history_json["huanqiu_world_last_time"] = int(
            requests.get(world_base_url.format(0), headers=HEADER).json().get("list")[0].get("ctime"))
        history_json_file.write(json.dumps(history_json, indent=4, sort_keys=True))

    end_time = time.time()
    print("Start time:{}\nEnd time:{}\ntotal time:{:.2f}".format(tools.time_stamp_for_13(int(start_time)),
                                                                tools.time_stamp_for_13(int(end_time)),
                                                                end_time - start_time))

