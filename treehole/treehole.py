import collections
import logging


import tornado.locale
import tornado.template

from .github import GithubClient, GithubIssue, GithubComment
from .utils import iso_8601_format_to_datetime



logger = logging.getLogger("treehole")



class IndexArchive:
    """首页输出最新三篇文章/内容列表归档实现，按日列出最新三篇文章列表（标题、日期、文章全部文本、精简标签显示）
    """


class DailyArchive:
    """按天文章列表归档实现，按日列出全部的文章列表（标题、日期、文章截断长文本、精简标签显示）
    """


class MonthlyArchive:
    """按月份文章列表归档实现，按日列出对应月份的文章列表（标题、日期、文章截断短文本、精简标签显示）
    """


class YearlyArchive:
    """按年份文章列表归档实现，按月份列出对应年份的文章列表（标题、日期）
    """
    def __init__(self, posts: list):
        self.posts = list(posts) # type: list[GithubIssue]

    def render(self):
        """遍历所有内容列表并生成年份对应列表
        """
        # 内容列表全部按照 created_at 从最旧到最新排序
        # 注意：此处是原地修改列表，没有数据复制
        sort_key = lambda post: iso_8601_format_to_datetime(post.get("created_at"))
        self.posts.sort(key=sort_key)

        # 按 年份 -> 月份 排序后归档列表数据结构如下
        # archive = Dict[int<Year>, Dict[int<Month>, List[issue]]]
        archive = collections.defaultdict(lambda: collections.defaultdict(list))
        for post in self.posts:
            created_at = post.get("created_at")
            year = created_at[0:4]  # 直接取前四位字符串作为年份，避免重复转换
            month = created_at[5:6] # 直接取第五第六位作为月份，避免重复转换
            archive[year][month].append(post)

        # 归档数据输出
        for year in sorted(archive.keys(), reverse=True):
            title = f"Archive for { year }"
            for month in sorted(archive[year].keys(), reverse=True):
                sub_title = f"Month {month}"
                for post in archive[year][month]:
                    post_title = f'{post.get("title")}'
       

class FeedArchive:
    """按 Feed/Atom 列表输出，按日列出最新十篇文章列表（标题、日期、文章截断长文本、精简标签显示）
    """
    template_name = None



class PostArchive:
    """按单一博客文章归档实现
    """
    template_name = "post.html"


