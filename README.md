# treehole

使用 Github Issues 作为后端的微型博客

> Microblog platform based Github issues

设计理念上，该微型博客就是一个巨大的内容列表/内容流，比传统微博/Twitter 多了个内容标题而已，内容部分可长可短，既可写成微博那样的三两句话/三两张图片记录新鲜事，又可用于整理观点写成文章，总之长度不限类型不限，纯粹内容瀑布流


## 产品特性

- 使用 Github Issues 作为博客管理后端/内容存储
    - Issues 本身作为微型博客输出为文章
    - Comments 则整理为列表输出为文章对应的评论列表
- 直接使用 Github Issues 本身作为内容管理
    - _编辑_：直接在 Github Issues 中编辑
    - _删除_：关闭对应的 Issue
    - _分类_：使用 Github Labels 进行内容分类/按标签分类
    - _置顶_：~~支持 Issues Pin 实现置顶文章~~
        - 由于 Github REST API 无此接口实现，暂无法实现置顶文章
- 支持 Github Reactions 作为内容的点赞功能
- 支持 Github Issue 内**直接上传图片并发布图片**，使用 Github CDN 加速/加载
- ~~完整使用 Github Markdown 渲染~~
    - 由于无法解决 `private-user-image` 的问题，此处改为本地渲染


## 技术细节

- 使用 Github Actions 根据 Issues 的增删改自动构建整个微型博客的内容
    - 增加 Issue Comments 不会重新构建整个网站
- 默认 Github Pages 作为微型博客的托管输出内容
- 所有 markdown 文档内容~~均使用 Github 内置的渲染输出，程序不处理任何的 markdown 渲染~~
    - 微型博客中 markdown 样式/css 样式同样使用 Github 内置的 markdown 样式**近似输出**
        - 缺少 TOC/目录、HeaderLink/标题锚点 等 Github 内置支持
    - 由于无法解决 `private-user-image` 的问题，此处改为本地渲染所有 markdown 格式
        - 可能存在部分不支持 GFM 的情况，比如 `#issue-number` 这样的引用
- 使用 `tornado.httpclient` 处理 Github APIv3 接口，仅使用与 Github Issues 简单的几个接口
    - 全异步请求实现，完整支持 AsyncIO 处理
    - 支持本地缓存接口请求数据，降低对 Github API 访问压力
- 使用 `tornado.templates` 解析并生成微型博客的全站的 HTML 模板并输出内容
    - 模板仅用于生成全站 HTML 内容
- 使用 `tornado.locale` 提供全站模板国际化翻译支持
    - 仅仅翻译模板类文本，非全文内容自动翻译
- 微型博客 `templates` 模板结构，仅保留最简单的内容模板
    - `base.html` 基础模板，用于微型博客全局页顶/页脚，全局模板支持
    - `list.html` 列表模板，用于微型博客内容列表，默认输出所有微型博客标题列表
        - 该模板用于微型博客首页
        - 该模板用于 daily/monthly/yearly 系列归档页面输出
    - `post.html` 内容模板，用于微型博客内容明细，默认输出单一内容全部字段
- 微型博客 `static` 静态文件
    - `app.css` 微型博客通用样式列表
        - 极其简洁/极简的全局/通用 css 代码实现，支持自动亮暗样式切换
    - `app.js` 微型博客脚本支持，仅用于评论功能支持
- 自动使用 `base_url` 对应的 `hostname` 生成对应的 `CNAME` 文件
    - 程序会自动生成 `.nojekyll` 以避免 Github Pages 自动使用 Jekyll 生成网站内容


## 为什么不

- 没有传统博客 `Pages/页面` 概念，没有 `About/关于` 页面，没有 `Archive/归档` 页面，没有 `LinkRoll/链接` 页面
    - 可以使用 Github Profile 进行自我介绍，进行作品展示
    - 需要特别说明的内容，~~可以使用 Issue Pin 置顶内容说明~~
        - 由于 Github REST API 无此接口实现，暂无法实现置顶文章
    - 微型博客**链接结构即内容结构**，无需重复实现归档页面
        - 程序内置按 daily/monthly/yearly 实现所有归档页面
- 没有传统博客 `Category/分类` 概念，没有 `Tags/标签` 概念
    - 只使用 Github Labels 进行内容分类，更细致更方便查找
        - 程序没有针对 Labels 单独页面进行文章内容归类/归类页面
    - 需要按 Github Labels 内容分类展示内容，可以使用 Github Issues 本身搜索
- 没有对应的搜索功能
    - 需要搜索内容，可以使用 Github Issues 本身搜索
    - 可以外挂外部自定义搜索引擎如 Google CSE
- 没有外挂评论实现 如 Disqus/Gitalk 
    - 需要评论只能前往 Github Issue Comments 本体发表评论
        - 所有 Comments 会在下次构建网站时输出为对应文章的评论列表
    - 可以使用 Github Reactions/emoji 对 Issue/Comment 本体点赞/点踩
    - 事实上，评论对于博客其实是伪需求，真需要讨论，**读者会直接邮件博主需求答复**
- 没有所谓的 `front-matter` 支持，写个简单的博客没有必要引入这样的别扭的数据


## 搜索优化

- 每篇内容统一使用 `/yyyy/mm/dd/[issue_id|slug]/` 唯一链接
    - 链接必须携带年/月/日，不可修改
    - 如果 Issue 标题是**只有英文**（含英文标点符号），那么可以生成对应的 `slug=slugify(title)` 内容链接
        - 中文内容优化：如果文章内存在至少一个 `h1` 标题且其文本与 `title` 不同，那么程序会抽取该 `h1` 标题为文章标题
    - 否则使用 Issue #ID 生成对应的内容链接
- 程序自动遍历全部内容并且生成以下链接内容，**链接结构即内容结构**
    - `/yyyy/` 将按月份列出对应年份的文章列表（标题、日期）
    - `/yyyy/mm/` 将按日列出对应月份的文章列表（标题、日期、文章截断短文本、精简标签显示）
    - `/yyyy/mm/dd/` 将按日列出全部的文章列表（标题、日期、文章截断长文本、精简标签显示）
- 每篇单一内容，程序会自动抽取对应的 [Open Graph](https://ogp.me) 方便外部引用/识别当前内容
    - 程序自动抽取第一个超过 130 字符的段落作为当前内容 summary
        - 如果整篇内容均不存在超过 130 字符的段落，则使用第一个不为空的段落作为 summary
    - 程序自动抽取嵌入文章的第一张图片（如有）作为文章头图
- 每篇单一内容，程序会自动生成对应的 `rel=canonical` 作为唯一链接
- 每篇单一内容，程序**不会生成**面向搜索引擎的结构化数据
    - 不会生成 `breadcrumb/面包屑导航` 内容链接已充分说明其层次关系
    - 不会生成 `Article/文章` 页面已有语义化的 HTML 实现
- 每篇单一内容，程序会自动计算其 Github Labels 相关性，得到**最多三篇**相关内容展示在内容结尾
    - 遍历筛选该内容所有 Labels 并针对每个 Label 筛选三篇相关内容
    - 计算所有得到的相关内容 Labels 与原内容 Labels 交集，按交集数量排序并筛选出最多三篇文章
- 每篇单一内容，程序会自动计算 Prev/Next 上一个/下一个文章内容，方便导航跳转
- 程序自动生成 `feedmap.xml` 和 `sitemap.xml`
    - 前者用于 RSS 跟踪更新，方便阅读器订阅
        - 只输出最新十篇内容，只输出内容摘要
    - 后者用于全站链接/网站地图，方便搜索引擎索引全部内容链接
        - 只输出所有内容唯一链接，不输出任何 daily/monthly/yearly 系列归档页面链接


## 备份计划

- 每次重新构建程序均会执行 backup/备份文件夹 生成，方便将数据同步至其他地方
    - 程序自动默认行为，没有配置项能修改此行为
- 备份分为两种
    - 原始 Github API Issues/Comments 接口返回数据，分别保存为 `_issues.json` 和 `_comments.json`
        - **调试状态下**，每次请求 Github API 接口均会重新生成
    - 所有 Issues 解析生成的 markdown 源文件则保存至 `backup` 目录中，方便直接点击阅读
        - 此处 backup/备份文件夹每次 build 都不会清理删除再写入，而是直接写入新文件
- 所有 backup/备份文件夹 内的文件按照 `[ISSUE_ID]_[ISSUE_TITLE].md` 规则生成文件名
- 执行 backup/备份文件夹 生成，有多种特殊情况
    - 如果修改了某个 issue 标题那么备份文件夹下会存在两个相同 issue_id 但标题不同的文件
    - 同样 issue_id 和标题，但是修改了内容，那么**后面修改的内容会覆盖前面的内容**
    - 上次 issue_id 已经写入备份，但下次 issue_id 已经关闭，那么备份会一直存在此 issue_id 
        - 网站生成的内容中不会再包含此 issue_id 的内容，但是 backup/备份文件夹 会保留
- 备份只会保存所有 issues 不会保存对应的 comments

