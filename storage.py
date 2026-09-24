import os
import boto3
from botocore.client import Config

# Cloudflare R2 is S3-compatible, so the regular boto3 S3 client works --
# we just point it at R2's endpoint instead of Amazon's.
_r2_client = None


def get_r2_client():
    global _r2_client
    if _r2_client is None:
        account_id = os.environ["R2_ACCOUNT_ID"]
        _r2_client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
    return _r2_client


def upload_file_to_r2(file_obj, key):
    """Upload a file-like object (e.g. from request.files) to R2 under `key`."""
    bucket = os.environ["R2_BUCKET_NAME"]
    get_r2_client().upload_fileobj(file_obj, bucket, key)
    return f"r2:{key}"  # stored in sales_file_path, prefixed so we can recognize it later


def delete_file_from_r2(key):
    bucket = os.environ["R2_BUCKET_NAME"]
    get_r2_client().delete_object(Bucket=bucket, Key=key)


def get_presigned_url(key, expires_in=300):
    """Generate a temporary (default 5-minute) signed URL to read a private R2 object."""
    bucket = os.environ["R2_BUCKET_NAME"]
    return get_r2_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )


def resolve_readable_path(sales_file_path):
    """
    Turn whatever is stored in Business.sales_file_path into something
    pandas can actually read directly.
    - "r2:<key>"      -> generate a fresh presigned URL (private R2 object)
    - anything else   -> already a real, directly-readable URL (e.g. a
                         published Google Sheets link) -- pass through unchanged
    """
    if sales_file_path.startswith("r2:"):
        key = sales_file_path[len("r2:"):]
        return get_presigned_url(key)
    return sales_file_path
