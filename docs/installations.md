# 程序安装使用

> 声明：如果你不是为了查看代码进行开发，仅仅是为了使用本程序，请不要直接 `git clone` 对应的仓库代码，而是应该使用 Release 页面中对应打包好的程序版本！！！

请前往 [TreeHole Release](https://github.com/mywaiting/treehole/releases) 页面下载对应的程序版本，建议直接选择最新版本代码即可

请选择如 `treehole-0.1-py3-none-any.whl` 或者 `treehole-0.1.tar.gz` 这样带版本号已经打包好的 Python Package

再次说明，请不要直接下载源代码使用，**源代码包含有 GNU Gettext 的翻译**，如果下载源代码到本地运行，则需要**首先编译 GNU Gettext 对应的翻译文件**，不然程序可能无法安装正常的预期工作

使用以下命令直接安装此 Python Package 即可

```bash

pip install treehole-0.1-py3-none-any.whl

# or 
pip install treehole-0.1.tar.gz

```

上述命令会自动安装 `treehole` 为本地 Python 包，而且会自动触发 pip 下载并安装这些依赖（如果本地尚未安装）

> 注意：上述命令不会安装 `optional-dependencies` 依赖，需要使用 `pip install treehole-0.1.tar.gz[doc]` 这样显式指定的命令才会安装对应的 `doc` 文档编译类依赖

安装完后，直接在 bash 中使用

```bash

treehole --help

```
