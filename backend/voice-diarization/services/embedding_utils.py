#!/usr/bin/env python3
"""
Embedding Utilities for Voice Diarization
Provides robust embedding strategies for speaker verification
"""

import os
import uuid
import tempfile
import logging
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


def l2norm_vec(x: np.ndarray) -> np.ndarray:
    """
    L2 normalize a vector.

    Args:
        x: Input vector

    Returns:
        L2-normalized vector
    """
    x = np.asarray(x, dtype=float)
    n = np.linalg.norm(x)
    return x / (n + 1e-12)  # Add epsilon to avoid division by zero


def get_embedding_for_wav(wav_path: str, speaker_model) -> np.ndarray:
    """
    Compute a (192,) embedding using TitaNet for a WAV file.

    Args:
        wav_path: Path to WAV file
        speaker_model: TitaNet model instance

    Returns:
        L2-normalized embedding vector of shape (192,)

    Raises:
        ValueError: If embedding shape is incorrect
    """
    import torch

    try:
        # Get embedding from model
        emb = speaker_model.get_embedding(wav_path)

        # Convert to numpy if needed
        if isinstance(emb, torch.Tensor):
            emb = emb.squeeze().cpu().numpy()
        else:
            emb = np.asarray(emb).squeeze()

        # Ensure float type
        emb = emb.astype(float)

        # Validate shape
        if emb.shape != (192,):
            raise ValueError(f"Expected (192,) embedding, got {emb.shape} for {wav_path}")

        # L2 normalize
        return l2norm_vec(emb)

    except Exception as e:
        logger.error(f"Error generating embedding for {wav_path}: {e}")
        raise


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """
    Calculate cosine similarity between two vectors.

    Args:
        a: First vector
        b: Second vector

    Returns:
        Cosine similarity score (0-1)
    """
    from sklearn.metrics.pairwise import cosine_similarity

    # Ensure 2D arrays for sklearn
    a = a.reshape(1, -1) if a.ndim == 1 else a
    b = b.reshape(1, -1) if b.ndim == 1 else b

    return float(cosine_similarity(a, b)[0][0])


def avg_embed_top_n_utterances(
    audio_segment,  # pydub.AudioSegment
    utterances: List[Dict[str, Any]],
    diarized_tag: str,
    speaker_model,
    top_n: int = 3
) -> Optional[np.ndarray]:
    """
    Average embeddings from the top_n longest utterances for a speaker.
    This provides a more robust embedding by using multiple samples.

    Args:
        audio_segment: Pydub AudioSegment of the full audio
        utterances: List of utterance dictionaries from AssemblyAI
        diarized_tag: Speaker label to process (e.g., "A", "B")
        speaker_model: TitaNet model instance
        top_n: Number of longest utterances to average

    Returns:
        L2-normalized averaged embedding vector or None if no utterances
    """
    from pydub import AudioSegment

    # Filter utterances for this speaker
    speaker_utts = [u for u in utterances if u["speaker"] == diarized_tag]
    if not speaker_utts:
        logger.debug(f"No utterances found for speaker {diarized_tag}")
        return None

    # Sort by duration and take top N
    top_utts = sorted(
        speaker_utts,
        key=lambda u: (u["end"] - u["start"]),
        reverse=True
    )[:top_n]

    embeddings = []

    for utterance in top_utts:
        start_ms = int(utterance["start"])
        end_ms = int(utterance["end"])

        # Extract audio segment
        segment = audio_segment[start_ms:end_ms]

        # Export to temporary WAV file
        temp_file = os.path.join(
            tempfile.gettempdir(),
            f"tmp_avg_{uuid.uuid4().hex[:8]}.wav"
        )

        try:
            # Export as mono WAV
            segment = segment.set_channels(1)
            segment = segment.set_frame_rate(16000)
            segment.export(temp_file, format="wav")

            # Generate embedding
            embedding = get_embedding_for_wav(temp_file, speaker_model)
            embeddings.append(embedding)

        finally:
            # Clean up temp file
            try:
                os.remove(temp_file)
            except:
                pass

    if not embeddings:
        logger.warning(f"Failed to generate embeddings for speaker {diarized_tag}")
        return None

    # Average embeddings
    avg_embedding = np.vstack(embeddings).mean(axis=0)

    # L2 normalize the average
    return l2norm_vec(avg_embedding)


def concat_and_embed_until_length(
    audio_segment,  # pydub.AudioSegment
    utterances: List[Dict[str, Any]],
    diarized_tag: str,
    speaker_model,
    target_ms: int = 8000,
    max_utts: int = 6
) -> Optional[np.ndarray]:
    """
    Concatenate utterances in chronological order until reaching target length.
    This provides a robust embedding from continuous speech.

    Args:
        audio_segment: Pydub AudioSegment of the full audio
        utterances: List of utterance dictionaries from AssemblyAI
        diarized_tag: Speaker label to process
        speaker_model: TitaNet model instance
        target_ms: Target total duration in milliseconds
        max_utts: Maximum number of utterances to concatenate

    Returns:
        L2-normalized embedding from concatenated audio or None
    """
    from pydub import AudioSegment

    # Filter and sort utterances chronologically
    speaker_utts = sorted(
        [u for u in utterances if u["speaker"] == diarized_tag],
        key=lambda u: u["start"]
    )

    if not speaker_utts:
        logger.debug(f"No utterances found for speaker {diarized_tag}")
        return None

    # Collect segments until target length
    pieces = []
    total_ms = 0
    count = 0

    for utterance in speaker_utts:
        start_ms = int(utterance["start"])
        end_ms = int(utterance["end"])

        # Extract segment
        segment = audio_segment[start_ms:end_ms]
        pieces.append(segment)

        total_ms += len(segment)
        count += 1

        if total_ms >= target_ms or count >= max_utts:
            break

    if not pieces:
        return None

    # Concatenate all pieces
    concatenated = pieces[0]
    for piece in pieces[1:]:
        concatenated += piece

    # Export to temporary file
    temp_file = os.path.join(
        tempfile.gettempdir(),
        f"tmp_cat_{uuid.uuid4().hex[:8]}.wav"
    )

    try:
        # Export as mono WAV
        concatenated = concatenated.set_channels(1)
        concatenated = concatenated.set_frame_rate(16000)
        concatenated.export(temp_file, format="wav")

        # Generate embedding
        embedding = get_embedding_for_wav(temp_file, speaker_model)
        return l2norm_vec(embedding)

    finally:
        # Clean up
        try:
            os.remove(temp_file)
        except:
            pass


def pick_suitable_snippet(
    utterances: List[Dict[str, Any]],
    speaker_tag: str,
    min_len_ms: int = 1000
) -> Optional[Dict[str, Any]]:
    """
    Choose the longest utterance for a speaker, preferring ones above minimum length.

    Args:
        utterances: List of utterance dictionaries
        speaker_tag: Speaker label to find
        min_len_ms: Preferred minimum length in milliseconds

    Returns:
        Best utterance dictionary or None
    """
    candidates = [u for u in utterances if u["speaker"] == speaker_tag]

    if not candidates:
        return None

    # Prefer utterances above minimum length
    long_enough = [
        u for u in candidates
        if (u["end"] - u["start"]) >= min_len_ms
    ]

    if long_enough:
        # Return longest utterance above threshold
        return max(long_enough, key=lambda u: u["end"] - u["start"])

    # Otherwise return longest available
    return max(candidates, key=lambda u: u["end"] - u["start"])


def get_robust_embedding(
    audio_segment,  # pydub.AudioSegment
    utterances: List[Dict[str, Any]],
    speaker_tag: str,
    speaker_model,
    min_utterance_ms: int = 1000
) -> Optional[np.ndarray]:
    """
    Get a robust embedding for a speaker using multiple strategies.
    Tries strategies in order of preference:
    1. Average top 3 longest utterances
    2. Concatenate utterances until 8+ seconds
    3. Use single longest utterance

    Args:
        audio_segment: Pydub AudioSegment
        utterances: List of utterances from transcript
        speaker_tag: Speaker label to process
        speaker_model: TitaNet model
        min_utterance_ms: Minimum utterance length preference

    Returns:
        L2-normalized embedding or None
    """
    from pydub import AudioSegment

    logger.debug(f"Getting robust embedding for speaker {speaker_tag}")

    # Strategy 1: Average top N utterances (most stable)
    embedding = avg_embed_top_n_utterances(
        audio_segment, utterances, speaker_tag, speaker_model, top_n=3
    )

    if embedding is not None:
        logger.debug(f"Used averaging strategy for {speaker_tag}")
        return embedding

    # Strategy 2: Concatenate until target length
    embedding = concat_and_embed_until_length(
        audio_segment, utterances, speaker_tag, speaker_model,
        target_ms=8000, max_utts=8
    )

    if embedding is not None:
        logger.debug(f"Used concatenation strategy for {speaker_tag}")
        return embedding

    # Strategy 3: Single longest utterance (fallback)
    chosen = pick_suitable_snippet(utterances, speaker_tag, min_utterance_ms)

    if chosen:
        start_ms = int(chosen["start"])
        end_ms = int(chosen["end"])

        # Extract segment
        segment = audio_segment[start_ms:end_ms]

        # Export to temp file
        temp_file = os.path.join(
            tempfile.gettempdir(),
            f"temp_{uuid.uuid4().hex[:8]}.wav"
        )

        try:
            segment = segment.set_channels(1)
            segment = segment.set_frame_rate(16000)
            segment.export(temp_file, format="wav")

            embedding = get_embedding_for_wav(temp_file, speaker_model)
            logger.debug(f"Used single utterance strategy for {speaker_tag}")
            return l2norm_vec(embedding)

        finally:
            try:
                os.remove(temp_file)
            except:
                pass

    logger.warning(f"Could not generate embedding for speaker {speaker_tag}")
    return None


def ensure_wav_mono(src_path: str, out_dir: str = None) -> str:
    """
    Convert any audio file to mono WAV format.

    Args:
        src_path: Source audio file path
        out_dir: Output directory (uses temp if None)

    Returns:
        Path to converted WAV file
    """
    from pydub import AudioSegment

    if out_dir is None:
        out_dir = tempfile.gettempdir()

    os.makedirs(out_dir, exist_ok=True)

    base = os.path.splitext(os.path.basename(src_path))[0]
    wav_path = os.path.join(out_dir, f"{base}.wav")

    # If already the target file, return
    if os.path.abspath(src_path) == os.path.abspath(wav_path) and os.path.exists(wav_path):
        return wav_path

    # Load and convert audio
    audio = AudioSegment.from_file(src_path)

    # Convert to mono
    if audio.channels > 1:
        audio = audio.set_channels(1)

    # Set sample rate to 16kHz (standard for speech)
    audio = audio.set_frame_rate(16000)

    # Export as WAV
    audio.export(wav_path, format="wav")

    logger.debug(f"Converted {src_path} to mono WAV at {wav_path}")
    return wav_path