from pathlib import Path

from botocore.exceptions import ClientError
from cached_property import cached_property

from ..manifest import AbstractManifest
from . import stack


class Manifest(AbstractManifest):
    id = "emr-spark-cluster"
    name = "EMR Spark Cluster"
    description = "EMR Spark Cluster to work with your events"
    install_warning = "This module creates an Amazon EMR cluster"

    @cached_property
    def ssh_keypair_name(self):
        return self.build_resource_name()

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
