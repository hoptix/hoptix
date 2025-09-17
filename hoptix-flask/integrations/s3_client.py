import boto3, json, os
from botocore.client import Config

def get_s3(region: str):
    return boto3.client("s3", region_name=region, config=Config(s3={"addressing_style": "virtual"}))

def create_multipart(s3, bucket: str, key: str, content_type: str = "audio/mpeg"):
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

def abort_multipart(s3, bucket: str, key: str, upload_id: str):
    s3.abort_multipart_upload(Bucket=bucket, Key=key, UploadId=upload_id)

def download_to_file(s3, bucket: str, key: str, dest_path: str, show_progress: bool = True):
    """Download a file from S3 with optional progress bar"""
    import logging
    from tqdm import tqdm
    
    logger = logging.getLogger(__name__)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    
    if show_progress:
        try:
            # Get file size for progress bar
            response = s3.head_object(Bucket=bucket, Key=key)
            file_size = response['ContentLength']
            
            # Create progress bar callback
            pbar = tqdm(total=file_size, unit='B', unit_scale=True, desc=f"📥 {os.path.basename(key)[:30]}")
            
            def progress_callback(bytes_transferred):
                pbar.update(bytes_transferred)
            
            logger.info(f"🔄 Starting S3 download: s3://{bucket}/{key}")
            s3.download_file(bucket, key, dest_path, Callback=progress_callback)
            pbar.close()
            
            # Log completion with file size
            actual_size = os.path.getsize(dest_path)
            logger.info(f"✅ Successfully downloaded from S3 ({actual_size:,} bytes) to: {dest_path}")
            
        except Exception as e:
            logger.warning(f"Could not show progress bar for S3 download: {e}")
            logger.info(f"🔄 Downloading from S3 without progress bar: s3://{bucket}/{key}")
            s3.download_file(bucket, key, dest_path)
            logger.info(f"✅ Successfully downloaded from S3 to: {dest_path}")
    else:
        logger.info(f"🔄 Downloading from S3: s3://{bucket}/{key}")
        s3.download_file(bucket, key, dest_path)
        logger.info(f"✅ Successfully downloaded from S3 to: {dest_path}")

def put_jsonl(s3, bucket: str, key: str, lines: list[dict]):
    body = "\n".join(json.dumps(x) for x in lines)
    s3.put_object(Bucket=bucket, Key=key, Body=body.encode("utf-8"), ContentType="application/jsonl")

def put_file(s3, bucket: str, key: str, local_path: str, content_type: str = None):
    extra = {"ContentType": content_type} if content_type else {}
    s3.upload_file(local_path, bucket, key, ExtraArgs=extra)