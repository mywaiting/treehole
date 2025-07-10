# treehole

使用 Github Issues 作为后端的微型博客

设计理念上，该微型博客就是一个巨大的内容列表/内容流，比传统微博/Twitter 多了个内容标题而已，内容部分可长可短，既可写成微博那样的三两句话/三两张图片记录新鲜事，又可用于整理观点写成文章，总之长度不限类型不限，纯粹内容瀑布流


## 产品特性

- 使用 Github Issues 作为博客管理后端/内容存储
    - Issues 本身作为微型博客输出为文章
    - Comments 则整理为列表输出为文章对应的评论列表
- 直接使用 Github Issues 本身作为内容管理
    - _编辑_：直接在 Github Issues 中编辑
    - _删除_：关闭对应的 Issue
    - _分类_：使用 Github Labels 进行内容分类/按标签分类
    - _置顶_：支持 Issues Pin 实现置顶文章
- 支持 Github Reactions 作为内容的点赞功能
- 支持 Github Issue 内直接上传图片并发布图片，使用 Github CDN 加速/加载
- 完整使用 Github Markdown 渲染


## 技术细节

- 使用 Github Actions 根据 Issues 的增删改自动构建整个微型博客的内容
    - 增加 Issue Comments 不会重新构建整个网站
- 默认 Github Pages 作为微型博客的托管输出内容
- 所有 markdown 文档内容均使用 Github 内置的渲染输出，程序不处理任何的 markdown 渲染
    - 微型博客中 markdown 样式同样使用 Github 内置的 markdown 样式输出
- 使用 `tornado.httpclient` 处理 Github APIv3 接口，仅使用与 Github Issues 简单的几个接口
    - 全异步请求实现，完整支持 AsyncIO 处理
- 使用 `tornado.templates` 解析并生成微型博客的全站的 HTML 模板并输出内容
    - 模板仅用于生成全站 HTML 内容
- 微型博客 `templates` 模板结构，仅保留最简单的内容模板
    - `base.html` 基础模板，用于微型博客全局页顶/页脚，全局模板支持
    - `list.html` 列表模板，用于微型博客内容列表，默认输出所有微型博客标题列表
        - 该模板用于微型博客首页
    - `post.html` 内容模板，用于微型博客内容明细，默认输出单一内容全部字段
- 微型博客 `static` 静态文件
    - `app.css` 微型博客通用样式列表
    - `app.js` 微型博客脚本支持，三几行代码用于支持 light/dark 模式切换


## 为什么不

- 没有传统博客 `Pages/页面` 概念，没有 `About/关于` 页面，没有 `Archive/归档` 页面，没有 `LinkRoll/链接` 页面
    - 可以使用 Github Profile 进行自我介绍，进行作品展示
    - 需要特别说明的内容，可以使用 Issue Pin 置顶内容说明
    - 微型博客首页就是内容列表，无需重复实现归档页面
- 没有传统博客 `Category/分类` 概念
    - 只使用 Github Labels 进行内容分类，更细致更方便查找
    - 需要按 Github Labels 内容分类展示内容，可以使用 Github Issues 本身搜索
- 没有对应的搜索功能
    - 需要搜索内容，可以使用 Github Issues 本身搜索
- 没有外挂评论实现 如 Disqus/Gitalk 
    - 需要评论只能前往 Github Issue Comments 本体发表评论
    - 事实上，评论对于博客其实是伪需求，真需要讨论，读者会直接邮件博主需求答复
- 没有所谓的 `front-matter` 支持，写个简单的博客没有必要引入这样的别扭的数据


## 搜索优化

- 每篇内容统一使用 `/yyyy/mm/dd/[issue_id|slug]/` 唯一链接
    - 链接必须携带年/月/日，不可修改
    - 如果 Issue 标题是英文，那么可以生成对应的 `slug=slugify(title)` 内容链接
        - 中文内容优化：如果文章内存在唯一的 `h1` 标题且其文本与 `title` 不同，那么程序会抽取该 `h1` 标题为文章标题
    - 否则使用 Issue #ID 生成对应的内容链接
- 程序自动遍历全部内容并且生成以下链接内容
    - `/yyyy/` 将按月份列出对应年份的文章列表（标题、日期）
    - `/yyyy/mm/` 将按日列出对应月份的文章列表（标题、日期、文章截断短文本、精简标签显示）
    - `/yyyy/mm/dd/` 将按日列出全部的文章列表（标题、日期、文章截断长文本、精简标签显示）
- 每篇单一内容，程序会自动抽取对应的 [Open Graph](https://ogp.me) 方便外部引用/识别当前内容
    - 程序自动抽取嵌入文章的第一张图片（如有）作为文章头图
- 每篇单一内容，程序会自动生成对应的 `rel=canonical` 唯一链接
- 每篇单一内容，程序**不会生成**面向搜索引擎的结构化数据
    - 不会生成 `breadcrumb/面包屑导航` 内容链接已经充分说明其层次关系
    - 不会生成 `Article/文章` 页面有语义化的 HTML 实现
- 每篇单一内容，程序会自动计算其 Github Labels 相关性，得到最多三篇的相关内容展示在内容结尾
    - 遍历筛选该内容所有 Labels 并针对每个 Label 筛选三篇相关内容
    - 计算所有得到的相关内容 Labels 与原内容 Labels 交集，按交集数量排序并筛选出最多三篇文章
- 每篇单一内容，程序会自动计算 Prev/Next 上一个/下一个文章内容，方便导航跳转
