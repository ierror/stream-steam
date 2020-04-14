from pathlib import Path

import jinja2

APP_MAIN_PATH = Path(__file__).parent.joinpath("ios").absolute()


def create_info_plist_file(tracking_server_url):
    tpl_loader = jinja2.FileSystemLoader(searchpath=APP_MAIN_PATH)
    tpl_env = jinja2.Environment(loader=tpl_loader)
    tpl = tpl_env.get_template("InfoTpl.plist")
    plist_content = tpl.render(tracking_server_url=tracking_server_url)
    plist_path = Path(APP_MAIN_PATH, "Info.plist")
    with plist_path.open("w") as fh:
        fh.write(plist_content)
    return plist_path
