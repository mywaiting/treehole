import logging
import os.path

import tornado.log
import tornado.options

from tornado.options import define, options

from .treehole import TreeHoleApp



define("debug", type=bool, default=True)
define("config", type=str)
define("default_locale", type=str, default="zh")
define("locale_domain", type=str, default="treehole")
define("base_url", type=str, default="https://treehole.io")
define("site_title", type=str, default="Treehole")
define("site_desc", type=str, default="Microblog platform based Github issues")
define("data_path", type=str, default="./data")
define("github_owner", type=str)
define("github_repo", type=str)
define("github_token", type=str)



base_dir = os.path.dirname(__file__)
logger = logging.getLogger("treehole")



def main():
    tornado.options.parse_command_line()

    # loaded default_settings.py
    if options.config:
        tornado.options.parse_config_file(options.config)
    else:
        default_settings = os.path.join(base_dir, "settings.py")
        if os.path.exists(default_settings):
            tornado.options.parse_config_file(default_settings)
        else:
            logger.info(f"no default_settings parsed")
    
    # 由于需要首先 parse_command_line/parse_config_file 才能得到完整的 options
    # 此处需要根据 debug 情况重新设置 logger.setLevel 的情况，否则全局日志无法打印
    if options.debug:
        logger.warning(f"TreeHole runas DEBUG mode")
        options.logging = "DEBUG"
        tornado.log.enable_pretty_logging(options)

    # loaded gettext/locale translations
    tornado.locale.load_gettext_translations(os.path.join(base_dir, "locale"), options.locale_domain)
    tornado.locale.set_default_locale(options.default_locale)

    app = TreeHoleApp(**options.as_dict())
    app.run()


main()