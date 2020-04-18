import platform
import subprocess
from pathlib import Path

import click
import jinja2
from cli import echo
from engine.stack import CloudformationStack

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


def demo_tracking_ios(cf_stack_name, cfg):
    @click.command(name="demo-tracking-ios")
    def _demo_tracking_ios():
        echo.h1("iOS Tracking Demo")

        if platform.system() == "Darwin":
            # create Info.plist with valid tracking URL
            cf_stack = CloudformationStack(cf_stack_name, cfg)
            plist_path = create_info_plist_file(f'{cf_stack.get_output("APIGatewayEndpoint")}/matomo.php')

            # open xCode
            echo.enum_elm("starting Xcode...")
            workspace = plist_path.parent.parent.joinpath("ios.xcworkspace")
            subprocess.call(f"open {workspace.absolute()}", shell=True)
            echo.enum_elm("start the Simulator to run the demo")
        else:
            echo.error("iOS demo only available on MacOS")

    return _demo_tracking_ios
