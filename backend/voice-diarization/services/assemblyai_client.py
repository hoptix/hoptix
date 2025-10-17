#!/usr/bin/env python3
"""
AssemblyAI Client for Voice Diarization
Handles transcription with speaker labels for multi-speaker audio
"""

import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def transcribe_with_speaker_labels(local_media_path: str) -> Dict[str, Any]:
    """
    Transcribe a LOCAL file with AssemblyAI and return json_response.

    Args:
        local_media_path: Path to local audio file

    Returns:
        Dict containing transcript with speaker-labeled utterances:
        {
            "utterances": [
                {
                    "speaker": "A",
                    "text": "Hi, what can I get you?",
                    "start": 0,
                    "end": 2000,
                    ...
                },
                ...
            ],
            "text": "Full transcript text",
            ...
        }

    Raises:
        RuntimeError: If AAI_API_KEY is not set
        Exception: If transcription fails
    """
    try:
        import assemblyai as aai
    except ImportError:
        raise ImportError(
            "assemblyai package not installed. "
            "Install with: pip install assemblyai"
        )

    # Get API key from environment
    aai_api_key = os.getenv('AAI_API_KEY')

    if not aai_api_key or aai_api_key.startswith("<"):
        raise RuntimeError(
            "AAI_API_KEY environment variable not set. "
            "Get your API key from https://www.assemblyai.com/dashboard"
        )

    logger.info(f"Transcribing {local_media_path} with AssemblyAI...")

    try:
        # Configure API
        aai.settings.api_key = aai_api_key

        # Create config with speaker labels enabled
        config = aai.TranscriptionConfig(
            speaker_labels=True  # Enable speaker diarization
        )

        # Create transcriber
        transcriber = aai.Transcriber(config=config)

        # Transcribe the file
        transcript = transcriber.transcribe(local_media_path)

        # Check for errors
        if transcript.status == "error":
            error_msg = getattr(transcript, 'error', 'Unknown error')
            raise Exception(f"Transcription failed: {error_msg}")

        # Return JSON response
        json_response = transcript.json_response

        # Validate response
        if not json_response:
            raise ValueError("Empty transcript response")

        utterances = json_response.get("utterances", [])
        if not utterances:
            logger.warning(
                "No utterances found in transcript. "
                "This might be a very short or silent audio file."
            )
        else:
            logger.info(
                f"Transcription complete: {len(utterances)} utterances, "
                f"{len(set(u['speaker'] for u in utterances))} speakers detected"
            )

        return json_response

    except Exception as e:
        logger.error(f"AssemblyAI transcription failed: {e}")
        raise


def validate_transcript(transcript_json: Dict[str, Any]) -> bool:
    """
    Validate that a transcript has the expected structure for speaker diarization.

    Args:
        transcript_json: Transcript JSON from AssemblyAI

    Returns:
        True if valid, False otherwise
    """
    if not transcript_json:
        return False

    # Check for utterances (required for speaker diarization)
    utterances = transcript_json.get("utterances", [])
    if not utterances:
        logger.warning("No utterances in transcript - speaker diarization not available")
        return False

    # Validate utterance structure
    required_fields = {"speaker", "text", "start", "end"}
    for i, utterance in enumerate(utterances):
        missing_fields = required_fields - set(utterance.keys())
        if missing_fields:
            logger.warning(
                f"Utterance {i} missing fields: {missing_fields}"
            )
            return False

    return True


def get_speaker_summary(transcript_json: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Get a summary of speakers from a transcript.

    Args:
        transcript_json: Transcript JSON from AssemblyAI

    Returns:
        Dict mapping speaker labels to statistics:
        {
            "A": {
                "utterance_count": 10,
                "total_duration_ms": 15000,
                "avg_utterance_ms": 1500,
                "first_utterance_ms": 0,
                "last_utterance_ms": 30000
            },
            ...
        }
    """
    utterances = transcript_json.get("utterances", [])
    if not utterances:
        return {}

    speaker_stats = {}

    for utterance in utterances:
        speaker = utterance["speaker"]
        start_ms = utterance["start"]
        end_ms = utterance["end"]
        duration_ms = end_ms - start_ms

        if speaker not in speaker_stats:
            speaker_stats[speaker] = {
                "utterance_count": 0,
                "total_duration_ms": 0,
                "first_utterance_ms": start_ms,
                "last_utterance_ms": end_ms,
                "utterances": []
            }

        stats = speaker_stats[speaker]
        stats["utterance_count"] += 1
        stats["total_duration_ms"] += duration_ms
        stats["last_utterance_ms"] = max(stats["last_utterance_ms"], end_ms)
        stats["first_utterance_ms"] = min(stats["first_utterance_ms"], start_ms)
        stats["utterances"].append(utterance)

    # Calculate averages
    for speaker, stats in speaker_stats.items():
        if stats["utterance_count"] > 0:
            stats["avg_utterance_ms"] = stats["total_duration_ms"] / stats["utterance_count"]
        else:
            stats["avg_utterance_ms"] = 0

    return speaker_stats


def filter_short_utterances(
    transcript_json: Dict[str, Any],
    min_duration_ms: int = 500
) -> Dict[str, Any]:
    """
    Filter out very short utterances that might be noise or single words.

    Args:
        transcript_json: Original transcript
        min_duration_ms: Minimum utterance duration to keep

    Returns:
        Filtered transcript with same structure
    """
    utterances = transcript_json.get("utterances", [])

    filtered_utterances = [
        u for u in utterances
        if (u["end"] - u["start"]) >= min_duration_ms
    ]

    if len(filtered_utterances) < len(utterances):
        logger.info(
            f"Filtered {len(utterances) - len(filtered_utterances)} "
            f"short utterances (< {min_duration_ms}ms)"
        )

    # Create new transcript with filtered utterances
    filtered_transcript = dict(transcript_json)
    filtered_transcript["utterances"] = filtered_utterances

    return filtered_transcript