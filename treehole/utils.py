# 
# 公共/辅助函数
# 

import datetime
import html.parser
import io
import os
import os.path
import re
import string
import unicodedata
import xml.etree.ElementTree as ET



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


def make_feedmap(feed_info, entries):
    """使用 ElementTree 实现的精简版 atom_feed.xml 生成器

    - 注意：此处要求 feed_info=dict(title=str, link=str, [updated=str]) 数据结构
    - 注意：此处要求 entries = list(dict(title=str, link=str, updated=str, summary=str)) 数据结构
    - 注意 ATOM Spec: http://atompub.org/2005/07/11/draft-ietf-atompub-format-10.html
    """
    mime_type = "application/atom+xml; charset=utf-8"
    ns = "http://www.w3.org/2005/Atom"

    feed = ET.Element("feed", { "xmlns": ns })

    # Feed 元信息
    title = ET.SubElement(feed, "title")
    title.text = feed_info.get("title", "My Feed")

    link = ET.SubElement(feed, "link", {"href": feed_info["link"]})

    updated = ET.SubElement(feed, "updated")
    updated.text = feed_info.get("updated", datetime.datetime.utcnow().isoformat() + "Z") # rfc3339_date

    id_tag = ET.SubElement(feed, "id")
    id_tag.text = feed_info.get("id", feed_info["link"])

    # Feed 条目
    for entry in entries:
        entry_tag = ET.SubElement(feed, "entry")

        entry_title = ET.SubElement(entry_tag, "title")
        entry_title.text = entry["title"]

        entry_link = ET.SubElement(entry_tag, "link", {"href": entry["link"]})

        entry_id = ET.SubElement(entry_tag, "id")
        entry_id.text = entry.get("id", entry["link"])

        entry_updated = ET.SubElement(entry_tag, "updated") # rfc3339_date
        entry_updated.text = entry["updated"]

        if "summary" in entry:
            entry_summary = ET.SubElement(entry_tag, "summary")
            entry_summary.text = entry["summary"]

    tree = ET.ElementTree(feed)
    fd = io.BytesIO()
    tree.write(fd, encoding="utf-8", xml_declaration=True)
    return fd.getvalue().decode("utf-8")


def make_sitemap(urls: list[dict(loc=str, lastmod=str)]):
    """使用 ElementTree 实现的精简版 sitemap.xml 生成器

    - 注意：此处要求 urls = [dict(loc=str, lastmod=str)] 必须存在 loc 字段
    """
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    urlset = ET.Element("urlset", { "xmlns": ns })

    for entry in urls:
        url = ET.SubElement(urlset, "url")
        loc = ET.SubElement(url, "loc")
        loc.text = entry["loc"]
        if "lastmod" in entry:
            lastmod = ET.SubElement(url, "lastmod")
            lastmod.text = entry["lastmod"]  # 应为 YYYY-MM-DD 格式

    tree = ET.ElementTree(urlset)
    fd = io.BytesIO()
    tree.write(fd, encoding='utf-8', xml_declaration=True)
    return fd.getvalue().decode("utf-8")


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

