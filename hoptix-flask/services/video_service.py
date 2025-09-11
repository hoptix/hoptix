import logging
from typing import List
from dateutil import parser as dateparse
from integrations.gdrive_client import parse_timestamp_from_filename

logger = logging.getLogger(__name__)

class VideoService:
    """Video-related utilities and helper functions."""
    
    @staticmethod
    def filter_videos_by_date(video_files: List, target_date: str) -> List:
        """Filter video files to only include those matching the target date"""
        target_date_obj = dateparse.parse(target_date).date()
        filtered_files = []
        
        for file_info in video_files:
            # Try to parse date from filename
            video_timestamp = parse_timestamp_from_filename(file_info['name'])
            
            if video_timestamp:
                video_date = video_timestamp.date()
                if video_date == target_date_obj:
                    filtered_files.append(file_info)
                    logger.info(f"Including {file_info['name']} (date: {video_date})")
                else:
                    logger.debug(f"Skipping {file_info['name']} (date: {video_date}, target: {target_date_obj})")
            else:
                logger.warning(f"Skipping {file_info['name']} (could not parse date from filename)")
        
        return filtered_files
