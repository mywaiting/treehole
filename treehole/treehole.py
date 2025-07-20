import asyncio
import collections
import copy
import datetime
import json
import logging
import os
import os.path
import shutil
import urllib.parse

import mistune
import tornado.locale
import tornado.template

from .github import GithubClient, GithubIssue, GithubComment, github_reactions
from .utils import (H1AndImageExtractor, only_english, from_iso8601_date, 
    slugify, fwrite, make_feedmap, make_sitemap)



base_dir = os.path.dirname(__file__)
logger = logging.getLogger("treehole")



# 
# models
# 

class TreeHolePost(dict):
    """TreeHole Post 单一文章数据模型，方便将外部数据转换到当前数据类型，并提前完成数据清洗
    """
    def __init__(self, post: dict):
        self._origin_data = post # type: dict[GithubIssue]

        self["id"] = post.get("issue_number")
        self["created_at"] = post.get("created_at")
        self["updated_at"] = post.get("updated_at")
        self["body"] = post.get("body")
        # 由于 Github 返回的 body_html 图片部分无法使用
        # 此处只能本地渲染 markdown 文档输出
        self["body_html"] = mistune.markdown(post.get("body"))

        # 抽取 body_html 中全部的 h1/img 内容作为标题/头图的参考
        parser = H1AndImageExtractor()
        parser.feed(self["body_html"] or "")
        parser.close()
        # 已经解析好的全部符合要求的 h1/img/p 内容
        parsed_titles = parser.titles
        parsed_images = parser.images
        parsed_paragraphs = parser.paragraphs

        # 计算当前所有时间，按帖子 created_at 时间戳计算
        dt = from_iso8601_date(post.get("created_at"))

        # 计算标题，请特别注意其 slugify 计算过程
        # 如果 Issue 标题是英文，那么可以生成对应的 `slug=slugify(title)` 内容链接
        #    - 中文内容优化：如果文章内存在唯一的 `h1` 标题且其文本与 `title` 不同，那么程序会抽取该 `h1` 标题为文章标题
        # 否则使用 Issue #ID 生成对应的内容链接
        title = post.get("title")
        if only_english(title):
            slug = slugify(title)
            if parsed_titles:
                title = parsed_titles[0]
            
            logger.info(f'parsed title={title}, slug={slug}')
        else:
            slug = slugify(post.get("issue_number"))
        
        # 计算当前文章是否存在题图/头图，默认使用第一张 Img 图片作为头图/题图
        if parsed_images:
            self["image"] = parsed_images[0]
        else:
            self["image"] = None
        
        # 计算得到当前文章全部段落，取出第一个不少于 130 长度的段落作为其简介/内容简介
        summary = ""
        for paragraph in parsed_paragraphs:
            if len(paragraph) > 130:
                summary = paragraph
                break
        # 如果此时 summary 不存在，那么默认使用第一个不为空段落作为其简介/内容简介
        if not summary:
            for paragraph in parsed_paragraphs:
                if paragraph:
                    summary = paragraph
                    break
        
        self["title"] = title
        self["slug"] = slug
        self["summary"] = summary
        self["permanent_url"] = f'/{dt.year}/{dt.month:02d}/{dt.day:02d}/{slug}/'               # 永久链接
        self["permanent_fullurl"] = f'/{dt.year}/{dt.month:02d}/{dt.day:02d}/{slug}/index.html' # 永久链接/全称形式，用于写入文件
        self["source_url"] = post.get("issue_url") # 原始链接
        self["labels"]  = post.get("labels")      # list
        self["reactions"] = post.get("reactions") # dict
        self["user"] = post.get("user")
        # 用于标识当前文件路径
        self["filepath"] = f'./{dt.year}/{dt.month:02d}/{dt.day:02d}/{slug}/index.html' # 当前文件路径


class TreeHoleComment(dict):
    """TreeHole Comment 单一评论数据模型
    """
    def __init__(self, comment: dict):
        self._origin_data = comment # type: dict[GithubComment]

        self["post_id"] = comment.get("issue_number")      # 原始 issue 序列号
        self["post_source_url"] = comment.get("issue_url") # 原始 issue 链接

        self["id"] = comment.get("comment_id")
        self["source_url"] = comment.get("comment_url") # 当前 comment 原始链接

        self["created_at"] = comment.get("created_at")
        self["updated_at"] = comment.get("updated_at")
        self["body"] = comment.get("body")
        # 由于 Github 返回的 body_html 图片部分无法使用
        # 此处只能本地渲染 markdown 文档输出
        self["body_html"] = mistune.markdown(comment.get("body"))

        self["reactions"] = comment.get("reactions") # list
        self["user"] = comment.get("user")


# 
# iters/archive
# 

class IndexArchive:
    """首页输出最新三篇文章/内容列表归档实现，按日列出最新三篇文章列表（标题、日期、文章全部文本、精简标签显示）
    """
    def __init__(self, posts: list[TreeHolePost]):
        self.posts = copy.deepcopy(posts)

        # 短暂为所有 posts 增加单独的 _datetime 字段用于排序和输出，避免重复转换
        for post in self.posts:
            post["_datetime"] = from_iso8601_date(post.get("created_at"))

        # 全部 posts 按照时间从最新到最旧排序，此处原地排序/逆序
        self.posts.sort(key=lambda post: post["_datetime"], reverse=True)

        # 首页只需要输出最新的三篇文章
        posts = self.posts[0:3]

        # 此处可以清理全部的 self.posts 此变量后面作为最终结果输出
        # 实际处理好的 posts 每个单一的元素都能单独输出为对应的 index_archive 页面
        self.posts = [{
            "filepath": "./index.html",
            "template_name": "list.html",
            "template_vars": {
                "page": "index",
                "page_title": None,  # 首页默认使用 site_title
                "page_desc": None,   # 首页默认使用 site_desc
                "page_class": "index",
                "posts": posts
            }
        }]

    def __iter__(self):
        return iter(self.posts)
    
    def __len__(self):
        return len(self.posts)


class DailyArchive:
    """按天文章列表归档实现，按日列出全部的文章列表（标题、日期、文章截断长文本、精简标签显示）
    """
    def __init__(self, posts: list[TreeHolePost]):
        self.posts = copy.deepcopy(posts)

        # 短暂为所有 posts 增加单独的 _datetime 字段用于排序和输出，避免重复转换
        for post in self.posts:
            post["_datetime"] = from_iso8601_date(post.get("created_at"))

        # 全部 posts 按照时间从最新到最旧排序，此处原地排序/逆序
        self.posts.sort(key=lambda post: post["_datetime"], reverse=True)

        # 构建 年 → 月 → 日 → [posts] 的嵌套结构
        posts = collections.defaultdict(         # year
            lambda: collections.defaultdict(     # month
                lambda: collections.defaultdict( # day
                    list                         # [posts]
                ) 
            )
        )

        # 遍历全部 posts 按照上述数据嵌套结构分类
        for post in self.posts:
            dt = post["_datetime"]
            posts[dt.year][dt.month][dt.day].append(post)
        
        # 此处可以清理全部的 self.posts 此变量后面作为最终结果输出
        # 实际处理好的 posts 每个单一的元素都能单独输出为对应的 daily_archive 页面
        self.posts = []

        # 遍历全部处理好的 posts 数据嵌套结构，按天汇总输出所有的 daily_archive 页面数据
        for year in sorted(posts.keys(), reverse=True):
            for month in sorted(posts[year].keys(), reverse=True):
                for day in sorted(posts[year][month].keys(), reverse=True):
                    current_day = datetime.date(year, month, day)
                    current_posts = posts[year][month][day]
                    
                    # 页面标题 weekday, day, month_name, year
                    title = f'{current_day.strftime("%A")}, {day}, {current_day.strftime("%B")}, {year}'
                    # 按日列出全部的文章列表（标题、日期、文章截断长文本、精简标签显示）
                    daily_posts = []
                    for post in current_posts:
                        daily_posts.append(post)

                    # 所有数据缓存到 self.posts 方便外部使用
                    self.posts.append({
                        "filepath": f"./{year}/{month:02d}/{day:02d}/index.html",
                        "template_name": "list.html",
                        "template_vars": {
                            "page": "daily",
                            "page_title": title,
                            "page_desc": title,
                            "page_class": "daily",
                            "posts": daily_posts
                        }
                    })
    
    def __iter__(self):
        return iter(self.posts)
    
    def __len__(self):
        return len(self.posts)
        

class MonthlyArchive:
    """按月份文章列表归档实现，按日列出对应月份的文章列表（标题、日期、文章截断短文本、精简标签显示）
    """
    def __init__(self, posts: list[TreeHolePost]):
        self.posts = copy.deepcopy(posts)

        # 短暂为所有 posts 增加单独的 _datetime 字段用于排序和输出，避免重复转换
        for post in self.posts:
            post["_datetime"] = from_iso8601_date(post.get("created_at"))

        # 全部 posts 按照时间从最新到最旧排序，此处原地排序/逆序
        self.posts.sort(key=lambda post: post["_datetime"], reverse=True)

        # 构建 年 → 月 → [posts] 的嵌套结构
        posts = collections.defaultdict(         # year
            lambda: collections.defaultdict(     # month
                lambda: collections.defaultdict( # day
                    list                         # [posts]
                ) 
            )
        )

        # 遍历全部 posts 按照上述数据嵌套结构分类
        for post in self.posts:
            dt = post["_datetime"]
            posts[dt.year][dt.month][dt.day].append(post)
        
        # 此处可以清理全部的 self.posts 此变量后面作为最终结果输出
        # 实际处理好的 posts 每个单一的元素都能单独输出为对应的 monthly_archive 页面
        self.posts = []

        # 遍历全部处理好的 posts 数据嵌套结构，按天汇总输出所有的 monthly_archive 页面数据
        for year in sorted(posts.keys(), reverse=True):
            for month in sorted(posts[year].keys(), reverse=True):
                # 页面标题
                month_dt = datetime.date(year, month, 1)
                title = f'{month_dt.strftime("%B")}, {year}'

                # 注意：此处将会执行按日检查，生成按日/daily 链接，不然无法导航到 daily_archive 页面
                # 注意：可能存在单日有多篇 posts 的情况，存在多篇 posts 的只显示一个按日/daily 链接
                _posts = []
                for day in sorted(posts[year][month].keys(), reverse=True):
                    # 将按日/daily 链接参考 post 的格式来生成，只有 title/permanent_url 两个字段
                    day_dt = datetime.date(year, month, day)
                    _posts.append({
                        "title": f'{day_dt.strftime("%B")} {day_dt.strftime("%d")}, {year}',
                        "permanent_url": f'/{day_dt.year}/{day_dt.month:02d}/{day_dt.day:02d}/'
                    })
                    # 接下来才是单日对应的 posts 文章列表
                    # 按日列出全部的文章列表（标题、日期、文章截断长文本、精简标签显示）
                    daily_posts = posts[year][month][day]
                    for post in daily_posts:
                        _posts.append(post)

                # 所有数据缓存到 self.posts 方便外部使用
                self.posts.append({
                    "filepath": f"./{year}/{month:02d}/index.html",
                    "template_name": "list.html",
                    "template_vars": {
                        "page": "monthly",
                        "page_title": title,
                        "page_desc": title,
                        "page_class": "daily",
                        "posts": _posts
                    }
                })
    
    def __iter__(self):
        return iter(self.posts)
    
    def __len__(self):
        return len(self.posts)


class YearlyArchive:
    """按年份文章列表归档实现，按月份列出对应年份的文章列表（标题、日期）
    """
    def __init__(self, posts: list[TreeHolePost]):
        self.posts = copy.deepcopy(posts)

        # 短暂为所有 posts 增加单独的 _datetime 字段用于排序和输出，避免重复转换
        for post in self.posts:
            post["_datetime"] = from_iso8601_date(post.get("created_at"))

        # 全部 posts 按照时间从最新到最旧排序，此处原地排序/逆序
        self.posts.sort(key=lambda post: post["_datetime"], reverse=True)

        # 构建 年 → 月 → [posts] 的嵌套结构
        posts = collections.defaultdict(     # year
            lambda: collections.defaultdict( # month
                list                         # [posts]
            )
        )

        # 遍历全部 posts 按照上述数据嵌套结构分类
        for post in self.posts:
            dt = post["_datetime"]
            posts[dt.year][dt.month].append(post)
        
        # 此处可以清理全部的 self.posts 此变量后面作为最终结果输出
        # 实际处理好的 posts 每个单一的元素都能单独输出为对应的 yearly_archive 页面
        self.posts = []

        # 遍历全部处理好的 posts 数据嵌套结构，按天汇总输出所有的 yearly_archive 页面数据
        for year in sorted(posts.keys(), reverse=True):
            # 页面标题
            title = f'Archive for {year}'

            # 注意：此处将会按月检查，生成按月/monthly 链接，不然无法导航到 monthly_archive
            _posts = []
            for month in sorted(posts[year].keys(), reverse=True):
                # 将按月/monthly 链接参考 post 的格式来生成，只有 title/permanent_url 两个字段
                month_dt = datetime.date(year, month, 1)
                _posts.append({
                    "title": f'{month_dt.strftime("%B")} ({len(posts[year][month])})',
                    "permanent_url": f'/{month_dt.year}/{month_dt.month:02d}/'
                })
                # 接下来才是月份对应的 posts 文章列表
                # 按日列出全部的文章列表（标题、日期、文章截断长文本、精简标签显示）
                monthly_posts = posts[year][month]
                # 当月内的文章，需要反向排序
                monthly_posts = list(reversed(monthly_posts))
                for post in monthly_posts:
                    _posts.append(post)

            # 所有数据缓存到 self.posts 方便外部使用
            self.posts.append({
                "filepath": f"./{year}/index.html",
                "template_name": "list.html",
                "template_vars": {
                    "page": "yearly",
                    "page_title": title,
                    "page_desc": title,
                    "page_class": "yearly",
                    "posts": _posts
                }
            })
    
    def __iter__(self):
        return iter(self.posts)
    
    def __len__(self):
        return len(self.posts)


class PostArchive:
    """按单一博客文章归档实现
    """
    def __init__(self, posts: list[TreeHolePost], comments: list[TreeHoleComment]):
        self.posts = copy.deepcopy(posts)
        self.comments = copy.deepcopy(comments)

        # 短暂为所有 comments 增加单独的 _datetime 字段用于排序和输出，避免重复转换
        for comment in self.comments:
            comment["_datetime"] = from_iso8601_date(comment.get("created_at"))

        # 全部 comments 按照时间从最新到最旧排序，此处原地排序/逆序
        self.comments.sort(key=lambda comment: comment["_datetime"], reverse=True)

        # 直接遍历处理得到所有按照 issue_number 的评论序列
        # 注意：此处显式转换数字为字符串作为 Key 务必注意！使用 Int 提取对应数据将返回 list()
        comments_maps = collections.defaultdict(list)
        for comment in self.comments:
            comments_maps[str(comment.get("post_id"))].append(comment)

        # 短暂为所有 posts 增加单独的 _datetime 字段用于排序和输出，避免重复转换
        for post in self.posts:
            post["_datetime"] = from_iso8601_date(post.get("created_at"))

        # 全部 posts 按照时间从最新到最旧排序，此处原地排序/逆序
        self.posts.sort(key=lambda post: post["_datetime"], reverse=True)

        # 构建 年 → 月 → [posts] 的嵌套结构
        posts = list(self.posts)

        # 构建根据 post_id 实现的查找字段
        posts_maps = { 
            post.get("id"): post
            for post in posts
        }

        # 计算两集合 Jaccard 相似度，比较简单
        def jaccard_similarity(set1: set[str], set2: set[str]):
            if not set1 and not set2:
                return 0.0
            return len(set1 & set2) / len(set1 | set2)
        
        # 单纯使用文章 post_id/labels.name 执行计算
        labels_maps = {
            post.get("id"): set(label.get("name") for label in post.get("labels"))
            for post in posts
        }
        labels_ids = list(labels_maps.keys())

        # 所有文章的相似度计算缓存
        similarity_maps = collections.defaultdict(list)
        for i in range(len(labels_ids)):
            for j in range(i + 1, len(labels_ids)):
                id1, id2 = labels_ids[i], labels_ids[j]
                sim = jaccard_similarity(labels_maps[id1], labels_maps[id2])
                if sim > 0.0:
                    similarity_maps[id1].append((id2, sim))
                    similarity_maps[id2].append((id1, sim))
        
        # 此处可以清理全部的 self.posts 此变量后面作为最终结果输出
        # 实际处理好的 posts 每个单一的元素都能单独输出为对应的 post_archive 页面
        self.posts = []

        # 遍历全部处理好的 posts 数据嵌套结构，按天汇总输出所有的 post_archive 页面数据
        for i, value in enumerate(posts):
            post = posts[i]
            prev_post = posts[i-1] if i > 0 else None              # 上一个文章/按当前文章顺序
            next_post = posts[i+1] if i < len(posts) - 1 else None # 下一个文章/按当前文章顺序
            # 得到当前文章，根据 labels 相似度计算的结果
            related = similarity_maps.get(post.get("id"), [])
            related_sorted = sorted(related, key=lambda x: x[1], reverse=True)[0:3] # 此处每次取三篇相似文章
            related_posts = [ posts_maps.get(post_id) for post_id, _ in related_sorted]
            # 所有数据缓存到 self.posts 方便外部使用
            self.posts.append({
                "filepath": post.get("filepath"), # 单一页面输出文件路径，直接提取其 filepath 此处不重复计算
                "template_name": "post.html",
                "template_vars": {
                    "page": "post",
                    "page_title": post.get("title"),
                    "page_desc": post.get("summary"),
                    "page_class": "single-post",
                    "post": post,
                    "prev_post": prev_post,
                    "next_post": next_post,
                    "related_posts": related_posts, # 根据 labels 计算得到的相似文章
                    "comments": comments_maps[str(post.get("id"))], # 注意：此处必须转换 id 为字符串
                }
            })
    
    def __iter__(self):
        return iter(self.posts)
    
    def __len__(self):
        return len(self.posts)


# 
# iters/generator
# 

class FeedmapGenerator:
    """按 Feed/Atom 列表输出，按日列出最新十篇文章列表（标题、日期、文章截断长文本、精简标签显示）
    """
    def __init__(self, posts: list[TreeHolePost], feed_info: dict, base_url: str):
        self.posts = copy.deepcopy(posts)

        # 短暂为所有 posts 增加单独的 _datetime 字段用于排序和输出，避免重复转换
        for post in self.posts:
            post["_datetime"] = from_iso8601_date(post.get("created_at"))

        # 全部 posts 按照时间从最新到最旧排序，此处原地排序/逆序
        self.posts.sort(key=lambda post: post["_datetime"], reverse=True)

        # Feed 只需要输出最新的十篇文章
        posts = self.posts[0:10]

        # 遍历所有 posts 得到 feed.entries 全部的数据
        entries = []
        for post in posts:
            entries.append({
                "title": post.get("title"),
                "link": urllib.parse.urljoin(base_url, post.get("permanent_url")),
                "updated": post.get("updated_at"), # rfc3339_date
                "summary": post.get("summary")
            })

        # 此处可以清理全部的 self.posts 此变量后面作为最终结果输出
        # 实际处理好的 posts 每个单一的元素都能单独输出为对应的 generator 页面
        self.posts = [{
            "filepath": "./feedmap.xml", # 文件输出路径
            "map_data": {
                "feed_info": feed_info,
                "entries": entries
            }
        }]

    def __iter__(self):
        return iter(self.posts)
    
    def __len__(self):
        return len(self.posts)


class SitemapGenerator:
    """输出 sitemap.xml 全站所有的 urls 
    """
    def __init__(self, posts: list[TreeHolePost], base_url: str):
        self.posts = copy.deepcopy(posts)

        # 短暂为所有 posts 增加单独的 _datetime 字段用于排序和输出，避免重复转换
        for post in self.posts:
            post["_datetime"] = from_iso8601_date(post.get("created_at"))

        # 全部 posts 按照时间从最旧到最新排序，此处**不要**原地排序/逆序
        self.posts.sort(key=lambda post: post["_datetime"])

        # Sitemap 需要输出全站所有的文章链接
        posts = []
        for post in self.posts:
            posts.append({
                "loc": urllib.parse.urljoin(base_url, post.get("permanent_url")),
                "lastmod": post.get("updated_at")
            })

        # 此处可以清理全部的 self.posts 此变量后面作为最终结果输出
        # 实际处理好的 posts 每个单一的元素都能单独输出为对应的 daily_archive 页面
        self.posts = [{
            "filepath": "./sitemap.xml",
            "map_data": {
                "urls": posts
            }
        }]

    def __iter__(self):
        return iter(self.posts)
    
    def __len__(self):
        return len(self.posts)


# 
# app
# 

class TreeHoleApp:
    def __init__(self, **settings):
        self.settings = settings

        self.settings.setdefault("locale_path", os.path.join(base_dir, "locale"))
        self.settings.setdefault("template_path", os.path.join(base_dir, "templates"))
        self.settings.setdefault("static_path", os.path.join(base_dir, "static"))

        data_path = self.settings.get("data_path")
        self.settings.setdefault("output_dir", os.path.join(data_path, "output"))
        
        if self.settings.get("cache_data", True):
            self.settings.setdefault("cache_issues", os.path.join(data_path, "_issues.json"))
            self.settings.setdefault("cache_comments", os.path.join(data_path, "_comments.json"))

    def clean_up(self):
        output_dir = self.settings.get("output_dir")
        logger.info(f'clean up folder: {output_dir}')

        for rel_path in os.listdir(output_dir):
            path = os.path.join(output_dir, rel_path)
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                try:
                    os.remove(path)
                except Exception as e:
                    logger.exception(f'no delete: {path}, exception: {e}')
    
    def load_data(self):
        """加载数据
        - debug 状态而且 ./data 目录有对应文件，那么从本地加载数据
        - 否则从 github 加载数据
        """
        cache_issues = self.settings.get("cache_issues")
        cache_comments = self.settings.get("cache_comments")

        if (self.settings.get("debug") and os.path.exists(cache_issues) and os.path.exists(cache_comments)):
            logger.info(
                f'use cache_data, issues={self.settings.get("cache_issues")}, '
                f'comments={self.settings.get("cache_comments")}'
            )
            with open(cache_issues, "rt") as fd:
                issues = json.load(fd)
            with open(cache_comments, "rt") as fd:
                comments = json.load(fd)
        
        else:
            owner = self.settings.get("github_owner")
            repo = self.settings.get("github_repo")
            token = self.settings.get("github_token")

            logger.info(f'use github_data, github_owner={owner}, github_repo={repo}')

            client = GithubClient(token)

            # 注意：此处需要将异步函数转为同步执行，注意下面的定义函数
            # 注意：由于函数返回异步生成器 yield+async 此处需要包裹中间的异步函数来执行
            async def get_repo_issues():
                issues = []
                async for issue in client.get_repo_issues(owner, repo):
                    issues.append(issue)
                return issues
            
            async def get_issue_comments():
                comments = []
                async for comment in client.get_issue_comments(owner, repo):
                    comments.append(comment)
                return comments

            # 异步函数转同步执行，更加方便
            loop = asyncio.get_event_loop()
            issues = loop.run_until_complete(get_repo_issues())
            comments = loop.run_until_complete(get_issue_comments())

            # 调试状态下缓存数据
            # 注意：此处是缓存 Github 接口返回的原始数据，方便后续 debug 使用
            if self.settings.get("debug"):
                logger.info(
                    f'save cache_data, issues={self.settings.get("cache_issues")}, '
                    f'comments={self.settings.get("cache_comments")}'
                )

                with open(cache_issues, "w") as fd:
                    json.dump(issues, fd, ensure_ascii=False, indent=2)
                with open(cache_comments, "w") as fd:
                    json.dump(comments, fd, ensure_ascii=False, indent=2)
        
        # 所有的数据按照 GithubModels 转换一遍
        issues = [ dict(GithubIssue(issue)) for issue in issues ]
        comments = [ dict(GithubComment(comment)) for comment in comments ]

        logger.info(f'count data before filters, issues={len(issues)}, comments={len(comments)}')

        # 跳过所有带有 pull_request 的 issue 这个没有必要出现在网站内容中
        issues = [ issue for issue in issues if "pull_request" not in issue ]
        # 筛选所有 issue.state='open' 的 issue 其余状态的 issue 不适宜出现在网站内容中
        issues = [ issue for issue in issues if issue.get("state") == "open" ]

        logger.info(f'count data after filters, issues={len(issues)}, comments={len(comments)}')

        # 所有数据按照 TreeHoleModels 再转换一遍，符合当前程序使用要求
        posts = [ dict(TreeHolePost(issue)) for issue in issues ]
        comments = [ dict(TreeHoleComment(comment)) for comment in comments ]

        return (posts, comments)

    def render(self, template_name: str, **kwargs):
        template_path = self.settings.get("template_path")
        template_kwargs = {
            "whitespace": "single"
        }
        loader = tornado.template.Loader(template_path, **template_kwargs)
        t = loader.load(template_name)
        locale = tornado.locale.get(self.settings.get("default_locale"))
        namespace = {
            "locale": locale,
            "_": locale.translate,
            "pgettext": locale.pgettext,
            # global template_vars
            "default_locale": self.settings.get("default_locale"),
            "base_url": self.settings.get("base_url"),
            "site_title": self.settings.get("site_title"),
            "site_desc": self.settings.get("site_desc"),
            # ui_methods
            "github_reactions":  github_reactions,
        }
        namespace.update(kwargs)

        # 注意：此处必须单独使用 try 方便直接显示出错的模板行数
        try:
            return t.generate(**namespace).decode()
        except Exception as e:
            logger.exception(f'fail to render: {template_name}, exception={e}')
            return ""

    def copy_file(self):
        static_path = self.settings.get("static_path")
        output_dir = self.settings.get("output_dir")

        logger.info(f'copy_file/static_file, from_dir={static_path}, to_dir={output_dir}')
        os.makedirs(output_dir, exist_ok=True)

        for rel_path in os.listdir(static_path):
            src_path = os.path.join(static_path, rel_path)
            dst_path = os.path.join(output_dir, rel_path)

            if os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
            else:
                shutil.copy2(src_path, dst_path)

    def run(self):
        logger.info(f'app started')

        # 首先清理输出目录
        self.clean_up()

        # 加载数据
        posts, comments = self.load_data()

        # 按照 Archive/归档 类别处理输出
        archives = {
            "index": IndexArchive(posts),
            "daily": DailyArchive(posts),
            "monthly": MonthlyArchive(posts),
            "yearly": YearlyArchive(posts),
            "post": PostArchive(posts, comments)
        }
        for archive, _posts in archives.items():
            logger.info(f'render {archive}, items={len(archives[archive])}')
            for post in _posts:
                filetext = self.render(post.get("template_name"), **post.get("template_vars"))
                fwrite(os.path.join(self.settings.get("output_dir"), post.get("filepath")), filetext)
        
        # 按照 Generator/生成器 类别处理输出
        feedmap = FeedmapGenerator(posts, {
                "title": self.settings.get("site_title"),
                "link": self.settings.get("base_url")
            }, self.settings.get("base_url")
        )
        sitemap = SitemapGenerator(posts, self.settings.get("base_url"))
        generators = {
            "feedmap": (feedmap, make_feedmap),
            "sitemap": (sitemap, make_sitemap)
        }
        for generator, t in generators.items():
            _posts, func = t
            logger.info(f'make {generator}, items={len(posts)}')
            for post in _posts:
                filetext = func(**post.get("map_data"))
                fwrite(os.path.join(self.settings.get("output_dir"), post.get("filepath")), filetext)

        # 复制静态文件
        self.copy_file()
        
        logger.info(f'app exited')

