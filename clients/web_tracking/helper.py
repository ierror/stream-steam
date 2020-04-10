import http.server
import os
import socketserver
import threading

import jinja2

HTTP_SERVE_ADDRESS = "127.0.0.1"
HTTP_SERVE_PORT = 1234
TPL_DIR = os.path.abspath(os.path.dirname(__file__))


def create_demo_index_file(tracking_server_url):
    tpl_loader = jinja2.FileSystemLoader(searchpath=TPL_DIR)
    tpl_env = jinja2.Environment(loader=tpl_loader)
    tpl = tpl_env.get_template("index_tpl.html")
    html = tpl.render(tracking_server_url=tracking_server_url)
    index_file = os.path.join(TPL_DIR, "index.html")
    with open(index_file, "w") as fh:
        fh.write(html)
    return index_file


def serve_demo():
    os.chdir(TPL_DIR)
    handler = http.server.SimpleHTTPRequestHandler
    httpd = socketserver.TCPServer((HTTP_SERVE_ADDRESS, HTTP_SERVE_PORT), handler)
    threading.Thread(target=httpd.serve_forever).start()
