import collections
import datetime
import logging


import tornado.locale
import tornado.template

from .github import GithubClient, GithubIssue, GithubComment
from .utils import H1AndImageExtractor, only_english, from_iso8601_date, slugify



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
        self["body_html"] = post.get("body_html")

        # 抽取 body_html 中全部的 h1/img 内容作为标题/头图的参考
        parser = H1AndImageExtractor()
        parser.feed(post.get("body_html"))
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
        self["permanent_url"] = f'/{dt.year}/{dt.month}/{dt.day}/{slug}/'               # 永久链接
        self["permanent_fullurl"] = f'/{dt.year}/{dt.month}/{dt.day}/{slug}/index.html' # 永久链接/全称形式，用于写入文件
        self["source_url"] = post.get("issue_url")                                      # 原始链接
        self["labels"]  = dict(post.get("labels"))
        self["reactions"] = dict(post.get("reactions"))
        self["user"] = dict(post.get("user"))


class IndexArchive:
    """首页输出最新三篇文章/内容列表归档实现，按日列出最新三篇文章列表（标题、日期、文章全部文本、精简标签显示）
    """
    template_name = "list.html"

    def __init__(self, posts: list[TreeHolePost]):
        self.posts = list(posts)

        # 短暂为所有 posts 增加单独的 _datetime 字段用于排序和输出，避免重复转换
        for post in self.posts:
            post["_datetime"] = from_iso8601_date(post.get("created_at"))

        # 全部 posts 按照时间从最新到最旧排序，此处原地排序/逆序
        self.posts.sort(key=lambda post: post["_datetime"], reverse=True)

        # 首页只需要输出最新的三篇文章
        posts = self.posts[0:3]

        # 此处可以清理全部的 self.posts 此变量后面作为最终结果输出
        # 实际处理好的 posts 每个单一的元素都能单独输出为对应的 daily_archive 页面
        self.posts = posts

    def __iter__(self):
        return iter(self.posts)
    
    def __len__(self):
        return len(self.posts)


class DailyArchive:
    """按天文章列表归档实现，按日列出全部的文章列表（标题、日期、文章截断长文本、精简标签显示）
    """
    template_name = "list.html"

    def __init__(self, posts: list[TreeHolePost]):
        self.posts = list(posts)

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
                    title = f'Archive for {current_day.strftime("%A")}, {day}, {current_day.strftime("%B")}, {year}'
                    # 按日列出全部的文章列表（标题、日期、文章截断长文本、精简标签显示）
                    daily_posts = []
                    for post in current_posts:
                        daily_posts.append(post)

                    # 所有数据缓存到 self.posts 方便外部使用
                    self.posts.append({
                        "title": title,
                        "posts": daily_posts
                    })
    
    def __iter__(self):
        return iter(self.posts)
    
    def __len__(self):
        return len(self.posts)
        

class MonthlyArchive:
    """按月份文章列表归档实现，按日列出对应月份的文章列表（标题、日期、文章截断短文本、精简标签显示）
    """
    def __init__(self, posts: list[TreeHolePost]):
        self.posts = list(posts)

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
                for day in sorted(posts[year][month].keys(), reverse=True):
                    current_day = datetime.date(year, month, day)
                    current_posts = posts[year][month][day]
                    
                    # 页面标题
                    title = f'Archive for {current_day.strftime("%B")}, {year}'
                    # 按日列出全部的文章列表（标题、日期、文章截断长文本、精简标签显示）
                    daily_posts = []
                    for post in current_posts:
                        daily_posts.append(post)

                    # 所有数据缓存到 self.posts 方便外部使用
                    self.posts.append({
                        "title": title,
                        "posts": daily_posts
                    })
    
    def __iter__(self):
        return iter(self.posts)
    
    def __len__(self):
        return len(self.posts)


class YearlyArchive:
    """按年份文章列表归档实现，按月份列出对应年份的文章列表（标题、日期）
    """
    def __init__(self, posts: list[TreeHolePost]):
        self.posts = list(posts)

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
        # 实际处理好的 posts 每个单一的元素都能单独输出为对应的 yearly_archive 页面
        self.posts = []

        # 遍历全部处理好的 posts 数据嵌套结构，按天汇总输出所有的 yearly_archive 页面数据
        for year in sorted(posts.keys(), reverse=True):
            for month in sorted(posts[year].keys(), reverse=True):
                for day in sorted(posts[year][month].keys(), reverse=True):
                    current_day = datetime.date(year, month, day)
                    current_posts = posts[year][month][day]
                    
                    # 页面标题
                    title = f'Archive for {year}'
                    # 按日列出全部的文章列表（标题、日期、文章截断长文本、精简标签显示）
                    daily_posts = []
                    for post in current_posts:
                        daily_posts.append(post)

                    # 所有数据缓存到 self.posts 方便外部使用
                    self.posts.append({
                        "title": title,
                        "posts": daily_posts
                    })
    
    def __iter__(self):
        return iter(self.posts)
    
    def __len__(self):
        return len(self.posts)


class PostArchive:
    """按单一博客文章归档实现
    """
    template_name = "post.html"

    def __init__(self, posts: list[TreeHolePost]):
        self.posts = list(posts)

        # 短暂为所有 posts 增加单独的 _datetime 字段用于排序和输出，避免重复转换
        for post in self.posts:
            post["_datetime"] = from_iso8601_date(post.get("created_at"))

        # 全部 posts 按照时间从最新到最旧排序，此处原地排序/逆序
        self.posts.sort(key=lambda post: post["_datetime"], reverse=True)

        # 构建 年 → 月 → [posts] 的嵌套结构
        posts = list(self.posts)
        
        # 此处可以清理全部的 self.posts 此变量后面作为最终结果输出
        # 实际处理好的 posts 每个单一的元素都能单独输出为对应的 post_archive 页面
        self.posts = []

        # 遍历全部处理好的 posts 数据嵌套结构，按天汇总输出所有的 post_archive 页面数据
        for i, value in enumerate(posts):
            current_post = posts[i]
            prev_post = posts[i-1] if i > 0 else None              # 上一个文章/按当前文章顺序
            next_post = posts[i+1] if i < len(posts) - 1 else None # 下一个文章/按当前文章顺序
            # 所有数据缓存到 self.posts 方便外部使用
            self.posts.append({
                "title": current_post.get("title"),
                "post": current_post,
                "prev_post": prev_post,
                "next_post": next_post
            })
    
    def __iter__(self):
        return iter(self.posts)
    
    def __len__(self):
        return len(self.posts)


class FeedArchive:
    """按 Feed/Atom 列表输出，按日列出最新十篇文章列表（标题、日期、文章截断长文本、精简标签显示）
    """


# 
# app
# 

class TreeHoleApp:
    def __init__(self, **settings):
        self.settings = settings

    def render_string(self, template_name: str, **kwargs):
        template_path = self.settings.get("template_path")
        loader = self.create_template_loader(template_path)
        t = loader.load(template_name)
        namespace = self.get_template_namespce()
        namespace.update(kwargs)
        return t.generate(**namespace)
    
    def get_template_namespce(self):
        code = self.settings.get("default_locale")
        locale = tornado.locale.get(code)
        namespace = dict(
            locale=locale,
            _=locale.translate,
            pgettext=locale.pgettext,
        )
        return namespace

    def create_template_loader(self, template_path: str):
        kwargs = {
            "autoescape": True,
            "whitespace": "single"
        }
        return tornado.template.Loader(template_path, **kwargs)



