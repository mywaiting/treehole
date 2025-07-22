# 国际化翻译指南

使用 GNU gettext 工具链在 Python 项目中进行完整翻译流程的步骤

1. 提取翻译字符串（`xgettext`）
2. 去重并优化（`msguniq`）
3. 创建/更新语言翻译文件（`msginit` / `msgmerge`）
4. 编辑翻译内容（编辑 .po 文件）
5. 编译为 .mo 机器文件（`msgfmt`）

## 准备工作：生成所有模板对应的 Python 代码文件

直接转换，或者直接使用 GNU Gettext 是无法处理 tornado.template 对应的文件的

使用以下代码实现即可转换 `template_path` 路径下全部的模板为对应命名的 `.$generated$.py` 文件，然后使用 GNU Gettext 提取所有 Python 文件源代码即可

```python

import pathlib
import tornado.template

template_path = pathlib.Path("./templates")
loader = tornado.template.Loader(template_path)

for file in template_path.rglob("*"):
    if file.suffix in [".html", ".htm", ".mail"]:
        rel_path = file.relative_to(template_path) # 编译模板需要相对路径
        full_path = template_path / rel_path       # 写入文件需要绝对路径
        t = loader.load(str(rel_path)) 
        with open(f"{str(full_path)}.$generated$.py", "wt") as fd:
            fd.write(t.code)

```

当然啦，在 `template_path` 路径下生成的全部模板代码文件，可以手动删除，也可以使用以下代码遍历删除，比如有很多级子目录的情况下

```python

import os
import pathlib

template_path = pathlib.Path("./templates")

for file in template_path.rglob("*"):
    if file.name.endswith(".$generated$.py"):
        os.unlink(str(file))

```

## 第一步：提取翻译字符串为 .pot 模板

默认使用 `./templates` 路径下面的全部的 Python 源文件

```bash

xgettext -L Python -o ./locale/messages.pot $(find ./templates -name '*.py')

```

> 特别注意，此处生成 `./locale/messages.pot` 文件后，需要手动处理修改其 `CHARSET=UTF-8`  不然后续会出现字符串编译错误

此处如果可以，请同步更新 Project 名称为 `TreeHole`

## 第二步：去重 .pot 文件（可选但推荐）

```bash

msguniq ./locale/messages.pot -o ./locale/messages.pot

```

## 第三步：初始化语言翻译（生成 .po 文件）

比如你要翻译为中文（简体），以下命令会生成一个 zh_CN.po 文件，初始内容来自 messages.pot

```bash

msginit --locale=zh_CN.UTF-8 --input=./locale/messages.pot --output=./locale/zh_CN.po

```

此处附带项目所有需要的命令，直接复制粘贴即可

```bash

# zh_CN
msginit --locale=zh_CN.UTF-8 --input=./locale/messages.pot --output=./locale/zh_CN/LC_MESSAGES/treehole.po

# zh_HK
msginit --locale=zh_HK.UTF-8 --input=./locale/messages.pot --output=./locale/zh_HK/LC_MESSAGES/treehole.po

# zh_TW
msginit --locale=zh_TW.UTF-8 --input=./locale/messages.pot --output=./locale/zh_TW/LC_MESSAGES/treehole.po

```

> 注意，上述命名仅仅用于**第一次** 生成对应语言的待翻译文件，如果已经存在翻译好 `treehole.po` 那么请跳过此步骤

## 第四步：更新已有翻译（用于项目后期维护）

此步骤仅适用已经存在翻译好 `treehole.po`，在更新 `./locale/messages.pot` 后，需要合并已有的翻译文本

特别注意，此步骤相当于合并已有的翻译，避免重复工作

```bash

# zh_CN
msgmerge --update ./locale/zh_CN/LC_MESSAGES/treehole.po ./locale/messages.pot

# zh_HK
msgmerge --update ./locale/zh_HK/LC_MESSAGES/treehole.po ./locale/messages.pot

# zh_TW
msgmerge --update ./locale/zh_TW/LC_MESSAGES/treehole.po ./locale/messages.pot

```

## 第五步：手动编辑 .po 文件翻译内容

.po 文件示例（使用编辑器打开）：

```pofile
msgid "Hello"
msgstr "你好"

msgid "Goodbye"
msgstr "再见"

```

你可以用文本编辑器（如 VSCode）编辑，也可以用 Poedit 工具图形化编辑。

其实直接上传到 ChatGPT 可以直接输出完整的翻译好的文件，一步到位完成处理！

## 第六步：编译 .po 为 .mo

.mo 是编译后的二进制文件，供程序（如 Flask/Django）运行时加载使用。

```bash

# zh_CN
msgfmt ./locale/zh_CN/LC_MESSAGES/treehole.po -o  ./locale/zh_CN/LC_MESSAGES/treehole.mo

# zh_HK
msgfmt ./locale/zh_HK/LC_MESSAGES/treehole.po -o  ./locale/zh_HK/LC_MESSAGES/treehole.mo

# zh_TW
msgfmt ./locale/zh_TW/LC_MESSAGES/treehole.po -o  ./locale/zh_TW/LC_MESSAGES/treehole.mo

```

你可以将它放入如下结构供加载使用：

```

locale/
  zh_CN/
    LC_MESSAGES/
      messages.mo

```

上面命令已经直接支持这样的目录结构，方便程序适用

