import platform
import subprocess
from pathlib import Path

import click
import jinja2
from cli import echo
from engine.stack import CloudformationStack

APP_MAIN_PATH = Path(__file__).parent.joinpath("app").absolute()


def create_app_gradle(tracking_server_url):
    tpl_loader = jinja2.FileSystemLoader(searchpath=APP_MAIN_PATH)
    tpl_env = jinja2.Environment(loader=tpl_loader)
    tpl = tpl_env.get_template("build.gradle.tpl")
    gardle_content = tpl.render(tracking_server_url=tracking_server_url)
    gardle_content_path = Path(APP_MAIN_PATH, "build.gradle")
    with gardle_content_path.open("w") as fh:
        fh.write(gardle_content)
    return gardle_content_path


def demo_tracking_android(cf_stack_name, cfg):
    @click.command(name="demo-tracking-android")
    def _demo_tracking_android():
        echo.h1("Android Tracking Demo")

        if platform.system() == "Darwin":
            # create Info.plist with valid tracking URL
            cf_stack = CloudformationStack(cf_stack_name, cfg)
            gradle_path = create_app_gradle(f'{cf_stack.get_output("APIGatewayEndpoint")}/matomo-event-receiver/')

            # open Android Studio
            echo.enum_elm("starting Android Studio...")
            workspace = gradle_path.parent
            subprocess.call(f"open -a /Applications/Android\ Studio.app {workspace.absolute()}", shell=True)
            echo.enum_elm("start the Simulator to run the demo")
        else:
            echo.error("Android demo only available on MacOS")

    return _demo_tracking_android
