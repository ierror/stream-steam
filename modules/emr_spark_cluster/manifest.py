from pathlib import Path

from botocore.exceptions import ClientError
from cached_property import cached_property
from cli import echo
from engine.stack import S3_ENRICHED_PREFIX

from ..manifest import AbstractManifest
from . import stack


class Manifest(AbstractManifest):
    id = "emr-spark-cluster"
    name = "EMR Spark Cluster"
    description = "EMR Spark Cluster to work with your events"
    install_warning = "This module creates an Amazon EMR cluster"

    def print_howto(self):
        echo.h1("How to connect to the cluster")

        echo.h2("connect via SSH to the master node")
        echo.code(
            f"ssh -i {self.ssh_keypair_path.absolute()} hadoop@{self.root_stack.get_output('EmrsparkclusterMasterPublicDNS')}"
        )

        echo.h2("start pyspark, wait for the session to be started")
        echo.code("pyspark")

        echo.h2("run the following example code")
        echo.code(
            f"df = spark.read.json('s3a://{self.root_stack.get_output('S3BucketName')}/{S3_ENRICHED_PREFIX}*/*/*/*/*.gz')"
        )
        echo.code("df.count()")
        echo.code(
            "df.groupBy('action_name', 'geo_info.city', 'device_info.device.name', 'device_info.device.type').count().show()"
        )
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
            keypair_path = self.ssh_keypair_path
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
        self.ssh_keypair_path.unlink(missing_ok=True)
