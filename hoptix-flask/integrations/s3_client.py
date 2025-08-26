import boto3, json, os
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

def download_to_file(s3, bucket: str, key: str, dest_path: str):
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    s3.download_file(bucket, key, dest_path)

def put_jsonl(s3, bucket: str, key: str, lines: list[dict]):
    body = "\n".join(json.dumps(x) for x in lines)
    s3.put_object(Bucket=bucket, Key=key, Body=body.encode("utf-8"), ContentType="application/jsonl")

def put_file(s3, bucket: str, key: str, local_path: str, content_type: str = None):
    extra = {"ContentType": content_type} if content_type else {}
    s3.upload_file(local_path, bucket, key, ExtraArgs=extra)