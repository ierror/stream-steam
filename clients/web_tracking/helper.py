import os

import jinja2


def create_demo_index_file(tracking_server_url):
    tpl_dir = os.path.abspath(os.path.dirname(__file__))
    tpl_loader = jinja2.FileSystemLoader(searchpath=tpl_dir)
    tpl_env = jinja2.Environment(loader=tpl_loader)
    tpl = tpl_env.get_template("index_tpl.html")
    html = tpl.render(tracking_server_url=tracking_server_url)
    index_file = os.path.join(tpl_dir, "index.html")
    with open(index_file, "w") as fh:
        fh.write(html)
    return index_file
