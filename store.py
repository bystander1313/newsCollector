import threading

import pymysql
import json
import os
from common import readconfig
from dbConnection import MySqlConn

# rc = readconfig.ReadConfig()
# news_info_store = os.path.join(os.getcwd(),
#                                rc.cf.get("Huanqiu-news", "news_info_store"))
# news_content_store = os.path.join(os.getcwd(),
#                                   rc.cf.get("Huanqiu-news", "news_content_store"))

# with open(news_info_store, "r") as new_info_fp:
#     news_info_json = json.load(new_info_fp)


class Write2MysqlThread(threading.Thread):
    def __init__(self, name):
        super(Write2MysqlThread, self).__init__(name=name)

    def run(self):
        while len(news_content_list) != 0:
            i = news_content_list.pop()
            mysql.insert(insert_sql, [i["ctime"], i["title"], i["time"], i["source"], i["summary"], i["content"]])

if __name__ == '__main__':
    global news_content_list
    global mysql
    global insert_sql

    insert_sql = "INSERT INTO news(ctime, title, time, source, summary, content) values (%s, %s, %s, %s, %s, %s)"
    # insert_sql = "INSERT INTO news_test(ctime, content) values (%s, %s)"

    mysql = MySqlConn.MyPymysqlPool("dbMysql")

    lock = threading.Lock()

    with open("./data/news-content.json", "r+") as json_file:
        json_file = json.load(json_file)

    news_content_list = json_file.pop()
    for i in json_file:
        mysql.insert(insert_sql, [i["ctime"], i["title"], i["time"], i["source"], i["summary"], i["content"]])

    threads = []
    for i in range(5):
        thread = Write2MysqlThread("t{}".format(i))
        threads.append(thread)

    for t in threads:
        t.start()

    while len(news_content_list) != 0:
        pass

    for t in threads:
        t.join()

    # 释放资源
    mysql.dispose()
