# 程序参数配置

整个 treehole 程序入口在 `treehole.__main__` 文件，请使用 Python Module 直接执行模块即可

```bash

cd treehole
python -m treehole --help

```

正常情况下有以下帮助菜单，需要的配置项目已经写得足够清晰了，请自行折腾

```bash

Usage: /developer/treehole/treehole/__main__.py [OPTIONS]

Options:

  --help                           show this help information

/developer/treehole/treehole/__main__.py options:

  --base-url                        (default https://treehole.io)
  --config
  --data-path                       (default ./data)
  --debug                           (default True)
  --default-locale                  (default en)
  --github-owner
  --github-repo
  --github-token
  --locale-domain                   (default treehole)
  --site-desc                       (default Microblog platform based Github
                                   issues)
  --site-title                      (default Treehole)

/home/vagrant/.pyenv/versions/venv3_12_3/lib/python3.12/site-packages/tornado/log.py options:

  --log-file-max-size              max size of log files before rollover
                                   (default 100000000)
  --log-file-num-backups           number of log files to keep (default 10)
  --log-file-prefix=PATH           Path prefix for log files. Note that if you
                                   are running multiple tornado processes,
                                   log_file_prefix must be different for each
                                   of them (e.g. include the port number)
  --log-rotate-interval            The interval value of timed rotating
                                   (default 1)
  --log-rotate-mode                The mode of rotating files(time or size)
                                   (default size)
  --log-rotate-when                specify the type of TimedRotatingFileHandler
                                   interval other options:('S', 'M', 'H', 'D',
                                   'W0'-'W6') (default midnight)
  --log-to-stderr                  Send log output to stderr (colorized if
                                   possible). By default use stderr if
                                   --log_file_prefix is not set and no other
                                   logging is configured.
  --logging=debug|info|warning|error|none
                                   Set the Python log level. If 'none', tornado
                                   won't touch the logging configuration.
                                   (default info)

```

考虑到实际部署需要，可以直接指定配置文件启动，配置文件可以使用 `--config` 参数指定其位置，该配置文件将会作为 Python 文件解析，并输出其中所有的值，以下是配置文件的例子

```python

# settings.py
# python -m treehole --config=./settings.py

base_url = "https://example.com" # 请修改为你要发布的网址，包含 http/https
debug = True
default_locale = "zh_CN"
github_owner = "mywaiting" # 你的 Github 用户名
github_repo = "treehole"   # 你的 Github 仓库名
site_title = "TreeHole"    # 发布网站的标题
site_desc = "Microblog platform based Github issues" # 网站简单描述

```

