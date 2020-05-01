from pathlib import Path

from botocore.exceptions import ClientError
from cached_property import cached_property
from cli import echo
from engine.stack import S3_TEPM_PREFIX

from ..manifest import AbstractManifest
from . import stack


class Manifest(AbstractManifest):
    id = "redash"
    name = "Redash EC2 Instance"
    description = '"Redash helps you make sense of your data" - https://redash.io'
    install_warning = "This module creates an Amazon EC2 instance"

    def print_howto(self):
        echo.h1("How to connect to redash")

        echo.h2("connect via HTTP to redash")
        echo.code(f"http://{self.root_stack.get_output('RedashServerIP')}")

        echo.h2("setup redash")
        echo.enum_elm(f"Name: {self.root_stack.name}")
        echo.enum_elm(f"AWS Region: {self.root_stack.region_name}")
        echo.enum_elm(f"AWS Access Key: {self.root_stack.cfg.get('aws_access_key_id')}")
        echo.enum_elm(f"AWS Secret Key (masked): {self.root_stack.cfg.get('aws_secret_access_key')[0:5]}************")
        echo.enum_elm(f"S3 Staging: s3://{self.root_stack.get_output('S3BucketName')}/{S3_TEPM_PREFIX}redash/")

        echo.h2("connect via SSH to the server")
        echo.code(f"ssh -i {self.ssh_keypair_path.absolute()} ubuntu@{self.root_stack.get_output('RedashServerIP')}")

        echo.info("")

    @cached_property
    def ssh_keypair_name(self):
        return self.build_resource_name()

    @cached_property
    def ssh_keypair_path(self):
        return Path("var", f"{self.ssh_keypair_name}.pem")

    @property
    def stack(self):
        return stack.build(self.ssh_keypair_name)

    def pre_deploy(self, *args, **kwargs):
        ec2 = self.root_stack.boto_session.client("ec2")
        try:
            keypair = ec2.create_key_pair(KeyName=self.ssh_keypair_name)
            keypair_path = Path("var", f"{self.ssh_keypair_name}.pem")
            keypair_path.write_text(keypair["KeyMaterial"])
            keypair_path.chmod(0o600)
        except ClientError as e:
            if hasattr(e, "response"):
                # already exists => ok
                if "InvalidKeyPair.Duplicate" not in str(e):
                    raise e
            else:
                raise e

    def post_deploy(self, *args, **kwargs):
        pass

    def pre_destroy(self, *args, **kwargs):
        pass

    def post_destroy(self, *args, **kwargs):
        ec2 = self.root_stack.boto_session.client("ec2")
        ec2.delete_key_pair(KeyName=self.ssh_keypair_name)
