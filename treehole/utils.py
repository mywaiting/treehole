# 
# 公共/辅助函数
# 

import datetime
import html.parser
import os
import os.path
import re
import string
import unicodedata



def fread(filepath):
    with open(filepath, "rt") as fd:
        return fd.read()


def fwrite(filepath, text):
    filepath = os.path.normpath(filepath)
    dirpath = os.path.dirname(filepath)

    # 首先创建父级文件夹
    os.makedirs(dirpath, exist_ok=True)

    with open(filepath, "wt") as fd:
        fd.write(text)


def slugify(value="", allow_unicode=False):
    """返回符合 URL要求的 slug url 格式 
    该函数抄袭自 django.utils.text.slugify 的实现

    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')


def from_iso8601_date(iso8601_date: str):
    """转换类似 2019-07-19T02:29:08Z/github 默认返回此类型数据 到 datetime 对象
    """
    dt = datetime.datetime.strptime(iso8601_date, "%Y-%m-%dT%H:%M:%SZ") # 带 Z 结尾表示当前时间为 UTC
    # 注意：此处必须指定这是 UTC 时间，否则可能会默认使用本地时区
    dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def to_rfc3389_date(dt: datetime.datetime):
    """将 datetime 转换为 RFC 3339 格式字符串
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)  # 默认为 UTC
    return dt.isoformat().replace('+00:00', 'Z')


def only_english(text: str):
    """是否只存在英文，包括英文符号/标点/数字
    """
    allowed_chars = set(
        string.ascii_letters + string.punctuation + string.whitespace + string.digits
    )
    return all(c in allowed_chars for c in text)


class H1AndImageExtractor(html.parser.HTMLParser):
    """遍历并提取全部 HTML 中的 H1/IMG/P 对应的内容并输出为列表

    使用方法：
        parser = H1AndImageExtractor()
        parser.feed("__HTML_HERE__")
        parser.close()
        print("Titles:", parser.titles)
        print("Images:", parser.images)
        print("Paragraphs:", parser.paragraphs)
    """
    def __init__(self):
        super().__init__()
        self.in_h1 = False
        self.in_p = False
        self.current_text = ""

        self.titles = []
        self.images = []
        self.paragraphs = []
    
    def handle_starttag(self, tag, attrs):
        if tag == 'h1':
            self.in_h1 = True
            self.current_text = ''
        elif tag == 'p':
            self.in_p = True
            self.current_text = ''
        elif tag == 'img':
            attrs_dict = dict(attrs)
            src = attrs_dict.get('src')
            if src:
                self.images.append(src)

    def handle_endtag(self, tag):
        if tag == 'h1' and self.in_h1:
            self.in_h1 = False
            self.titles.append(self.current_text.strip())
        elif tag == 'p' and self.in_p:
            text = self.current_text.strip()
            if text:
                self.paragraphs.append(text)
            self.in_p = False

    def handle_data(self, data):
        if self.in_h1 or self.in_p:
            self.current_text += data

