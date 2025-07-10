# 
# 公共/辅助函数
# 

import datetime
import io
import os
import os.path
import xml.sax.saxutils



def fread(filepath):
    with open(filepath, "rt") as fd:
        return fd.read()


def fwrite(filepath, text):
    base_dir = os.path.basename(filepath)
    if not os.path.isdir(base_dir):
        os.makedirs(base_dir, exist_ok=True)

    with open(filepath, "wt") as fd:
        fd.write(text)


def form_iso8601_date(iso8601_date: str):
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



class AtomFeedGenerator:
    """极其精简 ATOM Feed 生成器

    - 注意：代码逻辑参考自 https://github.com/getpelican/feedgenerator
    - 注意 ATOM Spec: http://atompub.org/2005/07/11/draft-ietf-atompub-format-10.html
    """
    mime_type = "application/atom+xml; charset=utf-8"
    ns = "http://www.w3.org/2005/Atom"

    def __init__(self, title, feed_id, updated=None):
        self.title = title
        self.feed_id = feed_id
        self.updated = updated or datetime.utcnow().isoformat() + 'Z'
        self.entries = []
    
    def add_entry(self, title, entry_id, updated, content):
        self.entries.append({
            'title': title,
            'id': entry_id,
            'updated': updated, # rfc3339_date
            'content': content,
        })
    
    def generate(self):
        buffer = io.StringIO()
        xml = xml.sax.saxutils.XMLGenerator(buffer, encoding='utf-8')
        xml.startDocument()
        xml.startElement("feed", {"xmlns": self.ns})

        # Feed metadata
        self._write_text_element(xml, "title", self.title)
        self._write_text_element(xml, "id", self.feed_id)
        self._write_text_element(xml, "updated", self.updated)

        # Entries
        for entry in self.entries:
            xml.startElement("entry", {})
            self._write_text_element(xml, "title", entry["title"])
            self._write_text_element(xml, "id", entry["id"])
            self._write_text_element(xml, "updated", entry["updated"])
            self._write_text_element(xml, "content", entry["content"], attrs={"type": "text"})
            xml.endElement("entry")

        xml.endElement("feed")
        xml.endDocument()
        return buffer.getvalue()

    def _write_text_element(self, xml, name, text, attrs=None):
        attrs = attrs or {}
        xml.startElement(name, attrs)
        xml.characters(text)
        xml.endElement(name)

