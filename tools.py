import time


def keyword_filter(keywords, title):
    if len(keywords) > 0:
        for keyword in keywords:
            if keyword not in title:
                return False
    return True


def time_stamp_for_13(ctime):
    time_stamp = float(ctime / 1000)  # 13位时间戳转换为10位
    time_array = time.localtime(time_stamp)
    other_style_time = time.strftime("%Y-%m-%d %H:%M:%S", time_array)
    return other_style_time


def getTimeStamp(time_str):
    ts = int(time.mktime(time.strptime(time_str, "%Y-%m-%d %H:%M:%S")))
    return ts


def assemble(news_list, news_content):
    full_info = []
    num = len(news_list)
    for i in range(num):
        one_in_list = news_list[i]
        one_in_list.append(news_content[i])
        full_info.append(one_in_list)
    return full_info


def write_one_in_csv(save_path, is_multiple, dates, titles, sources, contents, links):
    with open(save_path, "a+", encoding='utf-8', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["date", "title", "source", "content", "link"])
        if is_multiple:
            for i in range(len(dates)):
                writer.writerow([dates[i], titles[i], sources[i], contents[i], links[i]])
        else:
            writer.writerow()


def write_all_in_csv(save_path, all_info):
    with open(save_path, "a+", encoding='utf-8', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["date", "title", "source", "link", "content"])
        for item in all_info:
            writer.writerow(item)