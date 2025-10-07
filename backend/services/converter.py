# converts mkv to wav using ffmpeg
import pathlib
import subprocess

from dotenv import load_dotenv

load_dotenv()

def mkv_to_wav(input_path: str, output_path: str, sr: int = 16000, channels: int = 1):
    """
    Convert an .mkv file to .wav using ffmpeg.

    Args:
        input_path (str): Path to input .mkv file.
        output_path (str): Path to output .wav file (will overwrite if exists).
        sr (int): Target sample rate (default 16000).
        channels (int): Number of audio channels (default 1 = mono).

    Raises:
        subprocess.CalledProcessError: if ffmpeg fails
    """
    input_path = pathlib.Path(input_path)
    output_path = pathlib.Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",                   # overwrite existing files
        "-i", str(input_path),  # input file
        "-vn",                  # drop video
        "-acodec", "pcm_s16le", # uncompressed PCM
        "-ar", str(sr),         # sample rate
        "-ac", str(channels),   # channel count
        str(output_path)
    ]

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)

    return output_path

def get_duration(video_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "quiet", 
        "-show_entries", "format=duration", 
        "-of", "csv=p=0", 
        str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


    