from pathlib import Path

from botocore.exceptions import ClientError


def pre_deploy(boto_session, *args, **kwargs):
    ec2 = boto_session.client("ec2")
    try:
        keypair = ec2.create_key_pair(KeyName=globals()["MODULE_ENV"]["redash"]["KEY_PAIR_NAME"])
        keypair_path = Path("var", "redash.pem")
        keypair_path.write_text(keypair["KeyMaterial"])
        keypair_path.chmod(0o600)
    except ClientError as e:
        if hasattr(e, "response"):
            if "InvalidKeyPair.Duplicate" not in str(e):
                # already exists => ok
                raise e
        else:
            raise e


def pre_destroy(boto_session, *args, **kwargs):
    ec2 = boto_session.client("ec2")
    ec2.delete_key_pair(KeyName=globals()["MODULE_ENV"]["redash"]["KEY_PAIR_NAME"])
