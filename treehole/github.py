# 
# 使用 tornado.httpclient 实现的 Github APIv3 异步客户端
# 

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

    def __init__(self, token, accept="application/vnd.github.raw+json"):
        """
        - 注意：此处 accept 默认使用 raw+json 即可（本身就是默认值）
        - 注意：可以使用 full+json 是为了 issue/comments 直接返回 body_html 解析好的结果
        - 注意：本来是考虑直接使用 Github 原始生成的 body_html 结果的，但是有以下问题
            - 由于 Github 默认处理图片链接为 `https://private-user-images.githubusercontent.com/xxx.png?jwt={}`
                而且对应的图片由 `<a href=""></a>` 包裹，此处需要替换其链接实现
            - 处理好的图片链接最多只有五分钟的访问有效期，无法在文章输出中使用
            - 并且处理后的图片包裹对应图片链接，访问就直接出错，相当不友好
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
        
        logger.info(f'get_repo_issues, owner={owner}, repo={repo}, per_page={per_page}')
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
                logger.error(f"httpclient error: {e}", exc_info=True)
                response = e.response
                # 注意：此处出错则直接返回
                return
            except Exception as e:
                logger.error(f"httpclent unknown: {e}", exc_info=True)
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

        logger.info(f'get_issue_comments, owner={owner}, repo={repo}, per_page={per_page}')
        httpclient = tornado.httpclient.AsyncHTTPClient()

        while True:
            request = tornado.httpclient.HTTPRequest(url=url,
                method="GET",
                headers=self.headers,
                user_agent=self.user_agent
            )
            try:
                response = await httpclient.fetch(request)
                comments = json.loads(response.body)
            except tornado.httpclient.HTTPClientError as e:
                logger.error(f"httpclient error: {e}", exc_info=True)
                response = e.response
                # 注意：此处出错则直接返回
                return
            except Exception as e:
                logger.error(f"httpclent unknown: {e}", exc_info=True)
                # 注意：此处出错则直接返回
                return
            
            # 注意：此处返回迭代器方便直接使用当前返回结果
            # 注意：此处使用迭代器方便边拉取数据边使用数据，节省内存
            for comment in comments:
                yield comment

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

class GithubIssue(dict):
    """Github Issue 数据模型，方便转换到博客使用的数据类型
    """
    def __init__(self, issue: dict):
        self._origin_data = issue

        self["issue_url"] = issue.get("html_url")
        self["issue_number"] = issue.get("number")
        # issue
        self["title"] = issue.get("title")
        self["created_at"] = issue.get("created_at")
        self["updated_at"] = issue.get("updated_at")
        self["state"] = issue.get("state")
        self["body"] = issue.get("body")
        # self["body_html"] = issue.get("body_html")
        # labels
        self["labels"] = [ dict(GithubLabel(label)) for label in issue.get("labels") ]
        # reactions
        self["reactions"] = dict(GithubReactions(issue.get("reactions")))
        # user
        self["user"] = dict(GithubUser(issue.get("user")))


class GithubComment(dict):
    """Github Issue Comment 数据模型，方便转换到博客使用的数据类型
    """
    def __init__(self, comment: dict):
        self._origin_data = comment

        # https://api.github.com/repos/[owner]/[repo]/issues/[issue_number]
        # 注意：此处是直接替换得到对应 issue 网页版本的链接
        issue_url = comment.get("issue_url").replace("https://api.github.com/repos/", "https://github.com/")
        # 注意：此处是直接按 /issues/ 分割字符串得到对应的 issue_number
        _, issue_number = issue_url.split("/issues/", 1)

        # issue
        self["issue_url"] = issue_url
        self["issue_number"] = issue_number
        # comment
        self["comment_url"] = comment.get("html_url")
        self["comment_id"] = comment.get("id")
        self["created_at"] = comment.get("created_at")
        self["updated_at"] = comment.get("updated_at")
        self["body"] = comment.get("body")
        # self["body_html"] = comment.get("body_html")
        # reactions
        self["reactions"] = dict(GithubReactions(comment.get("reactions")))
        # user
        self["user"] = dict(GithubUser(comment.get("user")))


class GithubLabel(dict):
    """Github Issue Label 数据模型，方便转换到博客使用的数据类型
    """
    def __init__(self, label: dict):
        self._origin_data = label
        
        self["name"] = label.get("name")
        self["color"] = label.get("color")
        self["description"] = label.get("description")


class GithubReactions(dict):
    """Github Issue Reactions 数据模型，方便转换到博客使用的数据类型
    """
    def __init__(self, reactions: dict):
        self._origin_data = reactions

        self["+1"] = reactions.get("+1")
        self["-1"] = reactions.get("-1")
        self["laugh"] = reactions.get("laugh")
        self["hooray"] = reactions.get("hooray")
        self["confused"] = reactions.get("confused")
        self["heart"] = reactions.get("heart")
        self["rocket"] = reactions.get("rocket")
        self["eyes"] = reactions.get("eyes")    


class GithubUser(dict):
    """Github User 数据模型，方便转换到博客使用的数据类型
    """
    def __init__(self, user: dict):
        self._origin_data = user

        self["login"] = user.get("login")
        self["avatar_url"] = user.get("avatar_url")
        self["user_url"] = user.get("html_url")


# 
# utils
# 

def github_reactions(reaction: str):
    """返回所有 github emoji 表情
    """
    github_reactions = {
        "+1": "👍",         # Thumbs Up
        "-1": "👎",         # Thumbs Down
        "laugh": "😄",      # Laugh (smiley face)
        "hooray": "🎉",     # Hooray / Celebration
        "confused": "😕",   # Confused
        "heart": "❤️",      # Heart
        "rocket": "🚀",     # Rocket (often used for deployment/launch)
        "eyes": "👀"        # Eyes (watching/following)
    }
    if reaction not in github_reactions:
        return "YES"
    
    return github_reactions[reaction]

