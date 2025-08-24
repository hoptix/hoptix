#!/usr/bin/env python3
"""
Upload local test videos to S3 so they can be processed by the batch worker.
"""

import os
from dotenv import load_dotenv
from integrations.s3_client import get_s3
from config import Settings

load_dotenv()
settings = Settings()

def upload_test_videos():
    """Upload all .avi files from test_videos/ to S3"""
    s3 = get_s3(settings.AWS_REGION)
    
    test_dir = "test_videos"
    s3_prefix = "dev/sample"
    
    if not os.path.exists(test_dir):
        print(f"Directory {test_dir} not found!")
        return
    
    video_files = [f for f in os.listdir(test_dir) if f.endswith('.avi')]
    
    if not video_files:
        print(f"No .avi files found in {test_dir}/")
        return
    
    print(f"Found {len(video_files)} video files to upload:")
    
    for video_file in video_files:
        local_path = os.path.join(test_dir, video_file)
        s3_key = f"{s3_prefix}/{video_file}"
        
        print(f"  Uploading {video_file} -> s3://{settings.RAW_BUCKET}/{s3_key}")
        
        try:
            s3.upload_file(local_path, settings.RAW_BUCKET, s3_key)
            print(f"    ✅ Success")
        except Exception as e:
            print(f"    ❌ Failed: {e}")
    
    print(f"\nUpload complete! Videos are now available at:")
    for video_file in video_files:
        s3_key = f"{s3_prefix}/{video_file}"
        print(f"  s3://{settings.RAW_BUCKET}/{s3_key}")

if __name__ == "__main__":
    upload_test_videos()
