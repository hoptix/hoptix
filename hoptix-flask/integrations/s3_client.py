import boto3
from botocore.client import Config

def get_s3(region: str):
    return boto3.client("s3", region_name=region, config=Config(s3={"addressing_style": "virtual"}))

def create_multipart(s3, bucket: str, key: str, content_type: str = "video/mp4"):
    resp = s3.create_multipart_upload(Bucket=bucket, Key=key, ContentType=content_type)
    return resp["UploadId"]

def presign_parts(s3, bucket: str, key: str, upload_id: str, part_numbers: range, ttl: int):
    urls = []
    for pn in part_numbers:
        url = s3.generate_presigned_url(
            ClientMethod="upload_part",
            Params={"Bucket": bucket, "Key": key, "UploadId": upload_id, "PartNumber": pn},
            ExpiresIn=ttl,
        )
        urls.append(url)
    return urls

def complete_multipart(s3, bucket: str, key: str, upload_id: str, parts: list[dict]):
    s3.complete_multipart_upload(
        Bucket=bucket, Key=key, UploadId=upload_id, MultipartUpload={"Parts": parts}
    )