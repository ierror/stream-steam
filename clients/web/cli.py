import http.server
import os
import socketserver
import threading
from pathlib import Path
from webbrowser import open as webbrowser_open

import click
import jinja2
from cli import echo
from engine.stack import CloudformationStack

HTTP_SERVE_ADDRESS = "127.0.0.1"
HTTP_SERVE_PORT = 1234
APP_MAIN_PATH = Path(__file__).parent


def create_demo_index_file(tracking_server_url):
    tpl_loader = jinja2.FileSystemLoader(searchpath=APP_MAIN_PATH.absolute())
    tpl_env = jinja2.Environment(loader=tpl_loader)
    tpl = tpl_env.get_template("index.html.tpl")
    html = tpl.render(tracking_server_url=tracking_server_url)
    index_file = Path(APP_MAIN_PATH, "index.html")
    with index_file.open("w") as fh:
        fh.write(html)
    return index_file


def serve_demo():
    os.chdir(APP_MAIN_PATH)
    handler = http.server.SimpleHTTPRequestHandler
    httpd = socketserver.TCPServer((HTTP_SERVE_ADDRESS, HTTP_SERVE_PORT), handler)
    threading.Thread(target=httpd.serve_forever).start()


def demo_tracking_web(cf_stack_name, cfg):
    @click.command(name="demo-tracking-web")
    def _demo_tracking_web():
        echo.h1("Web Tracking Demo")
        serve_url = f"http://{HTTP_SERVE_ADDRESS}:{HTTP_SERVE_PORT}/"

        # create index.html
        cf_stack = CloudformationStack(cf_stack_name, cfg)
        create_demo_index_file(f'{cf_stack.get_output("APIGatewayEndpoint")}/event-receiver/')

        # serve the demo
        echo.enum_elm(f"serving demo at {serve_url}")
        echo.enum_elm("quit the server with <strg|control>-c.")
        echo.info("")
        serve_demo()

        # open browser
        webbrowser_open(serve_url)

    return _demo_tracking_web
