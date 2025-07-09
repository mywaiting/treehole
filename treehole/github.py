# 
# 使用 tornado.httpclient 实现的 Github APIv3 异步客户端
# 

import datetime
import json
import logging
import urllib.parse

import tornado.httpclient
import tornado.httputil



logger = logging.getLogger("treehole")



# 
# client
# 

class GithubClient:
    """Github API Client
    """
    base_url = "https://api.github.com"
    user_agent = "python-github-client"
    api_version = "2022-11-28"
    api_reference = "https://docs.github.com/"

    def __init__(self, token, accept="application/vnd.github.html+json"):
        """注意：此处 accept 默认使用 html+json 是为了 issue/comments 直接返回 body_html 解析好的结果
        """
        self.token = token
        self.accept = accept
        self.headers = {
            "Accept": f"{accept}",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": f"{self.api_version}"
        }

    async def get_repo_issues(self,
        owner: str,
        repo: str,
        state: str = "all",
        per_page = 100
    ):
        """返回对应仓库的全部的 issues

        - 注意：使用 accept=application/vnd.github.html+json 才能返回 body_html 字段方便后续直接使用
        - 注意：返回数据中已经默认带上每个 issue 对应的 reactions
        """
        # GET /repos/{owner}/{repo}/issues <https://docs.github.com/en/rest/reference/issues>
        params = {
            "creator": owner, # 注意：此处强制返回仓库拥有者创建的 issues
            "state": state,
            "per_page": per_page
        }
        url = f"{self.base_url}/repos/{owner}/{repo}/issues?{urllib.parse.urlencode(params)}"

        httpclient = tornado.httpclient.AsyncHTTPClient()

        while True:
            request = tornado.httpclient.HTTPRequest(url=url,
                method="GET",
                headers=self.headers,
                user_agent=self.user_agent
            )
            try:
                response = await httpclient.fetch(request)
                issues = json.loads(response.body)
            except tornado.httpclient.HTTPClientError as e:
                logger.error(f"httpclient error: {e}")
                response = e.response
                # 注意：此处出错则直接返回
                return
            
            # 注意：此处返回迭代器方便直接使用当前返回结果
            # 注意：此处使用迭代器方便边拉取数据边使用数据，节省内存
            for issue in issues:
                yield issue

            links = self.parse_header_links(response.headers)
            # 注意：如果存在 next 说明还有下一页，否则不存在下一页
            # 注意：此处 next 对应的链接已经包含 params 无需再单独指定
            if "next" in links:
                url = links.get("next")
            
            # 注意：此处已经无下一页，直接跳出循环
            else:
                break
    
    async def get_issue_comments(self,
        owner: str,
        repo: str,
        per_page = 100
    ):
        """返回对应 issues 全部 comments

        - 注意：使用 accept=application/vnd.github.html+json 才能返回 body_html 字段方便后续直接使用
        - 注意：返回数据中已经默认带上每个 comment 对应的 reactions
        """
        # GET /repos/{owner}/{repo}/issues/comments <https://docs.github.com/en/rest/reference/issues#comments>
        params = {
            "per_page": per_page
        }
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/comments?{urllib.parse.urlencode(params)}"

        httpclient = tornado.httpclient.AsyncHTTPClient()

        while True:
            request = tornado.httpclient.HTTPRequest(url=url,
                method="GET",
                headers=self.headers,
                user_agent=self.user_agent
            )
            try:
                response = await httpclient.fetch(request)
                issues = json.loads(response.body)
            except tornado.httpclient.HTTPClientError as e:
                logger.error(f"httpclient error: {e}")
                response = e.response
                # 注意：此处出错则直接返回
                return
            
            # 注意：此处返回迭代器方便直接使用当前返回结果
            # 注意：此处使用迭代器方便边拉取数据边使用数据，节省内存
            for issue in issues:
                yield issue

            links = self.parse_header_links(response.headers)
            # 注意：如果存在 next 说明还有下一页，否则不存在下一页
            # 注意：此处 next 对应的链接已经包含 params 无需再单独指定
            if "next" in links:
                url = links.get("next")
            
            # 注意：此处已经无下一页，直接跳出循环
            else:
                break

    def parse_header_links(self, headers: tornado.httputil.HTTPHeaders):
        """Github 使用 link Headers 作为分页链接，此处为解析过程

        docs: https://docs.github.com/rest/using-the-rest-api/using-pagination-in-the-rest-api
        """
        links = {} # prev/next/first/last
        if headers and "link" in headers and isinstance(headers["link"], str):
            link_headers = headers["link"].split(", ")
            for link_header in link_headers:
                url, rel, *rest = link_header.split("; ")
                url = url[1:-1]
                rel = rel[5:-1]
                links[rel] = url
        
        return links



# 
# models
# 

class GithubData:
    def to_dict(self):
        if hasattr(self, "_to_dict_data"):
            return self._to_dict_data
        
        return {}

    def iso_time_to_timestamp(self, iso_time):
        """转换类似 2019-07-19T02:29:08Z 到默认的 UNIX 时间戳
        """
        # 注意：带 Z 结尾表示当前时间为 UTC
        dt = datetime.datetime.strptime(iso_time, "%Y-%m-%dT%H:%M:%SZ")
        # 注意：此处必须指定这是 UTC 时间，否则可能会默认使用本地时区
        dt = dt.replace(tzinfo=datetime.timezone.utc)
        # 返回默认时间戳
        return int(dt.timestamp())


class GithubIssue(GithubData):
    """Github Issue 数据模型，方便转换到博客使用的数据类型
    """
    def __init__(self, issue: dict):
        self.issue = issue
        self._to_dict_data = {
            "issue_url": issue.get("html_url"),
            "issue_number": issue.get("number"),
            # issue
            "title": issue.get("title"),
            "created_at": self.iso_time_to_timestamp(issue.get("created_at")),
            "updated_at": self.iso_time_to_timestamp(issue.get("updated_at")),
            "state": issue.get("state"),
            "body": issue.get("body"),
            "body_html": issue.get("body_html"),
            # labels
            "labels": [ GithubLabel(label).to_dict() for label in issue.get("labels") ],
            # reactions
            "reactions": GithubReactions(issue.get("reactions")).to_dict(),
            # user
            "user": GithubUser(issue.get("user")).to_dict()
        }


class GithubComment(GithubData):
    """Github Issue Comment 数据模型，方便转换到博客使用的数据类型
    """
    def __init__(self, comment: dict):
        self.comment = comment

        # https://api.github.com/repos/[owner]/[repo]/issues/[issue_number]
        # 注意：此处是直接替换得到对应 issue 网页版本的链接
        issue_url = comment.get("issue_url").replace("https://api.github.com/repos/", "https://github.com/")
        # 注意：此处是直接按 /issues/ 分割字符串得到对应的 issue_number
        _, issue_number = issue_url.split("/issues/", 1)

        self._to_dict_data = {
            # issue
            "isuue_url": issue_url,
            "issue_number": issue_number,
            # comment
            "comment_url": comment.get("html_url"),
            "comment_id": comment.get("id"),
            "created_at": self.iso_time_to_timestamp(comment.get("created_at")),
            "updated_at": self.iso_time_to_timestamp(comment.get("updated_at")),
            "body": comment.get("body"),
            "body_html": comment.get("body_html"),
            # reactions
            "reactions": GithubReactions(comment.get("reactions")).to_dict(),
            # user
            "user": GithubUser(comment.get("user")).to_dict()
        }


class GithubLabel(GithubData):
    """Github Issue Label 数据模型，方便转换到博客使用的数据类型
    """
    def __init__(self, label: dict):
        self.label = label
        self._to_dict_data = {
            "name": label.get("name"),
            "color": label.get("color"),
            "description": label.get("description")
        }


class GithubReactions(GithubData):
    """Github Issue Reactions 数据模型，方便转换到博客使用的数据类型
    """
    def __init__(self, reactions: dict):
        self.reactions = reactions
        self._to_dict_data = {
            "+1": reactions.get("+1"),
            "-1": reactions.get("-1"),
            "laugh": reactions.get("laugh"),
            "hooray": reactions.get("hooray"),
            "confused": reactions.get("confused"),
            "heart": reactions.get("heart"),
            "rocket": reactions.get("rocket"),
            "eyes": reactions.get("eyes")
        }


class GithubUser(GithubData):
    """Github User 数据模型，方便转换到博客使用的数据类型
    """
    def __init__(self, user: dict):
        self.user = user
        self._to_dict_data = {
            "login": user.get("user"),
            "avatar_url": user.get("avatar_url"),
            "user_url": user.get("html_url")
        }

