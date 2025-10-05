import sys
import os
import datetime

# Ensure project root is on path for imports when running pytest
sys.path.insert(0, os.path.abspath('.'))

from integrations.gdrive_client import parse_timestamp_from_filename
from services.video_service import VideoService


def test_parse_timestamp_from_audio_mp3_filename():
    filename = "audio_2025-10-04_10-00-01.mp3"
    dt = parse_timestamp_from_filename(filename)
    assert dt is not None
    assert dt.year == 2025
    assert dt.month == 10
    assert dt.day == 4
    assert dt.hour == 10
    assert dt.minute == 0
    assert dt.second == 1


def test_filter_includes_audio_mp3_for_date():
    target_date = "2025-10-04"
    files = [
        {"id": "1", "name": "audio_2025-10-04_10-00-01.mp3", "mimeType": "audio/mpeg"},
        {"id": "2", "name": "audio_2025-10-03_10-00-01.mp3", "mimeType": "audio/mpeg"},
        {"id": "3", "name": "DQ Cary_20251004-20251004_1000.mkv", "mimeType": "video/x-matroska"},
    ]

    filtered = VideoService.filter_videos_by_date(files, target_date)
    filtered_names = {f["name"] for f in filtered}

    assert "audio_2025-10-04_10-00-01.mp3" in filtered_names
    assert "audio_2025-10-03_10-00-01.mp3" not in filtered_names
    assert "DQ Cary_20251004-20251004_1000.mkv" in filtered_names


