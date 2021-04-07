# import pymysql
#
# db = pymysql.connect(host="localhost", user="root", password="123456", database="test")
# cursor = db.cursor()
# cursor.execute("SELECT * FROM comoditytype")
# data = cursor.fetchall()
# print(data)
# db.close()
#

import requests
from bs4 import BeautifulSoup
import re
import lxml
import json

def parse_response(res):
    res.encoding = 'utf-8'
    print(res.text)
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
    print(str_data)
    return str_data


if __name__ == '__main__':
    res = requests.get("https://world.huanqiu.com/article/42bFZPwWEa7")
    print(parse_response(res))

    with open("data/news-content.back", 'ab+') as json_file:
        json_file.seek(-2, 2)
        json_file.write(b"]")
    #     ts = json_file.read()
    #     print(ts)
    # #     dict = json.load(json_file)
    # print(dict)