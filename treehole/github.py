# 
# 使用 tornado.httpclient 实现的 Github APIv3 异步客户端
# 

import json
import logging
import urllib.parse

import tornado.httpclient
import tornado.httputil



logger = logging.getLogger("treehole")



class Github:
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

            links = parse_header_links(response.headers)
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

            links = parse_header_links(response.headers)
            # 注意：如果存在 next 说明还有下一页，否则不存在下一页
            # 注意：此处 next 对应的链接已经包含 params 无需再单独指定
            if "next" in links:
                url = links.get("next")
            
            # 注意：此处已经无下一页，直接跳出循环
            else:
                break



# 
# utils
# 

def parse_header_links(headers: tornado.httputil.HTTPHeaders):
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

