import configparser
import os


class ReadConfig:
    """定义一个读取配置文件的类"""

    def __init__(self, filepath=None):
        if filepath:
            configpath = filepath
        else:
            root_dir = os.path.abspath('.')
            configpath = os.path.join(root_dir, "config/config.ini")
        self.cf = configparser.RawConfigParser()
        self.cf.read(configpath)

