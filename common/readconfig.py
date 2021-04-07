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

    def get_sections(self):
        return self.cf.sections()

    def get_options(self, section):
        return self.cf.options(section)

    def get_content(self, section):
        result = {}
        for option in self.get_options(section):
            value = self.cf.get(section, option)
            result[option] = int(value) if value.isdigit() else value
        return result