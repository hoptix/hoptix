#!/usr/bin/env python3
"""
Speaker Matching for Voice Diarization
Identifies speakers in transcripts and matches them to known workers
"""

import os
import glob
import logging
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
from pydub import AudioSegment

from .embedding_utils import (
    l2norm_vec,
    cosine_sim,
    get_embedding_for_wav,
    get_robust_embedding,
    ensure_wav_mono
)

logger = logging.getLogger(__name__)


def filename_to_label(path: str) -> str:
    """
    Convert filename to nice label.
    Example: 'Cary_Office01.wav' -> 'Cary Office01'

    Args:
        path: File path

    Returns:
        Cleaned label
    """
    stem = os.path.splitext(os.path.basename(path))[0]
    return stem.replace("_", " ").strip()


def build_local_embeddings(
    samples_dir: str,
    speaker_model,
    supported_exts: set = {".wav", ".mp3", ".m4a"}
) -> Dict[str, np.ndarray]:
    """
    Build embeddings for all voice samples in a directory.

    Args:
        samples_dir: Directory containing voice samples
        speaker_model: TitaNet model instance
        supported_exts: Supported audio file extensions

    Returns:
        Dict mapping worker names to embedding vectors
    """
    logger.info(f"Building embeddings from samples in {samples_dir}")

    # Find all audio files
    sample_paths = []
    for ext in supported_exts:
        sample_paths.extend(glob.glob(os.path.join(samples_dir, f"*{ext}")))

    sample_paths = sorted(sample_paths)

    if not sample_paths:
        logger.warning(f"No audio files found in {samples_dir}")
        return {}

    local_embeddings = {}

    for sample_path in sample_paths:
        try:
            # Get clean label from filename
            label = filename_to_label(sample_path)

            # Convert to WAV if needed
            wav_path = ensure_wav_mono(sample_path)

            # Generate embedding
            embedding = get_embedding_for_wav(wav_path, speaker_model)
            local_embeddings[label] = embedding

            logger.info(f"  ✓ Embedded: {label}")

            # Clean up temp file if created
            if wav_path != sample_path and os.path.exists(wav_path):
                try:
                    os.remove(wav_path)
                except:
                    pass

        except Exception as e:
            logger.error(f"Failed to embed {sample_path}: {e}")

    logger.info(f"Built embeddings for {len(local_embeddings)} workers")
    return local_embeddings


def identify_speakers_in_transcript(
    transcript_json: Dict[str, Any],
    wav_path: str,
    speaker_model,
    local_embeddings: Dict[str, np.ndarray],
    threshold: float = 0.2,
    min_utterance_ms: int = 1000
) -> Tuple[List[Dict], Dict[str, bool]]:
    """
    Map diarized speakers to known workers using robust embeddings.

    Args:
        transcript_json: AssemblyAI transcript with utterances
        wav_path: Path to audio file
        speaker_model: TitaNet model
        local_embeddings: Worker name to embedding mapping
        threshold: Minimum similarity threshold
        min_utterance_ms: Minimum utterance length preference

    Returns:
        Tuple of (relabeled_utterances, presence_map)
    """
    utterances = transcript_json.get("utterances", [])
    if not utterances:
        raise ValueError("No utterances found in transcript")

    logger.info(f"Identifying speakers in transcript with {len(utterances)} utterances")

    # Load audio
    audio = AudioSegment.from_wav(wav_path)

    # Map diarized labels (A, B, C) to worker names
    diarized_to_label = {}

    # Get unique speakers
    diarized_speakers = sorted(set(u["speaker"] for u in utterances))
    logger.info(f"Found {len(diarized_speakers)} diarized speakers: {diarized_speakers}")

    for diarized_speaker in diarized_speakers:
        # Get robust embedding for this speaker
        embedding = get_robust_embedding(
            audio, utterances, diarized_speaker,
            speaker_model, min_utterance_ms
        )

        if embedding is None:
            logger.warning(f"No usable audio for speaker {diarized_speaker}")
            diarized_to_label[diarized_speaker] = "No match"
            continue

        # Compare to all known workers
        best_label = "No match"
        best_score = 0.0

        for worker_name, worker_embedding in local_embeddings.items():
            # Ensure normalized
            ref_embedding = l2norm_vec(np.asarray(worker_embedding, dtype=float))

            # Calculate similarity
            score = cosine_sim(embedding, ref_embedding)

            if score > best_score:
                best_label = worker_name
                best_score = score

        # Apply threshold
        if best_score < threshold:
            logger.info(
                f"Speaker '{diarized_speaker}' -> 'No match' "
                f"(best={best_label}, score={best_score:.3f} < {threshold})"
            )
            diarized_to_label[diarized_speaker] = "No match"
        else:
            logger.info(
                f"Speaker '{diarized_speaker}' -> '{best_label}' "
                f"(score={best_score:.3f})"
            )
            diarized_to_label[diarized_speaker] = best_label

    # Relabel utterances with worker names
    relabeled = []
    for utterance in utterances:
        new_utterance = dict(utterance)
        new_utterance["speaker_original"] = utterance["speaker"]
        new_utterance["speaker"] = diarized_to_label.get(
            utterance["speaker"], "No match"
        )
        relabeled.append(new_utterance)

    # Build presence map
    presence = {label: False for label in local_embeddings.keys()}
    for utterance in relabeled:
        if utterance["speaker"] in presence:
            presence[utterance["speaker"]] = True

    return relabeled, presence


def run_pipeline_on_media_best_match(
    local_media_path: str,
    speaker_model,
    local_embeddings: Dict[str, np.ndarray],
    transcript_json: Optional[Dict] = None,
    threshold: float = 0.2,
    min_utterance_ms: int = 1000
) -> Tuple[str, float, List[Dict], Dict[str, bool]]:
    """
    Run full pipeline and return the BEST matching speaker.
    This is the key difference from threshold-based matching - we pick
    the speaker with the highest similarity score overall.

    Args:
        local_media_path: Path to audio file
        speaker_model: TitaNet model
        local_embeddings: Worker embeddings
        transcript_json: Optional pre-computed transcript
        threshold: Minimum similarity threshold
        min_utterance_ms: Minimum utterance length

    Returns:
        Tuple of (best_label, best_score, relabeled_utterances, presence)
    """
    from .assemblyai_client import transcribe_with_speaker_labels

    logger.info(f"Running best-match pipeline on {local_media_path}")

    # Convert to WAV if needed
    wav_path = ensure_wav_mono(local_media_path)

    # Transcribe if not provided
    if transcript_json is None:
        transcript_json = transcribe_with_speaker_labels(wav_path)

    # Identify speakers
    relabeled_utterances, presence = identify_speakers_in_transcript(
        transcript_json=transcript_json,
        wav_path=wav_path,
        speaker_model=speaker_model,
        local_embeddings=local_embeddings,
        threshold=threshold,
        min_utterance_ms=min_utterance_ms
    )

    # Now find the BEST matching speaker
    raw_utterances = transcript_json.get("utterances", [])
    audio = AudioSegment.from_wav(wav_path)

    best_score = 0.0
    best_label = "No match"

    # Get unique identified speakers (excluding "No match")
    unique_speakers = set(u["speaker"] for u in relabeled_utterances)
    unique_speakers.discard("No match")

    logger.info(f"Evaluating {len(unique_speakers)} identified speakers for best match")

    for speaker_name in unique_speakers:
        # Get all diarized tags that mapped to this speaker
        mapped_tags = sorted(set(
            u["speaker_original"] for u in relabeled_utterances
            if u["speaker"] == speaker_name
        ))

        # Build combined embedding for all tags
        emb_parts = []
        for tag in mapped_tags:
            # Get embedding for this diarized tag
            embedding = get_robust_embedding(
                audio, raw_utterances, tag,
                speaker_model, min_utterance_ms
            )
            if embedding is not None:
                emb_parts.append(embedding)

        if emb_parts:
            # Average all embeddings for this speaker
            combined_embedding = l2norm_vec(np.vstack(emb_parts).mean(axis=0))

            # Compare to reference
            ref_embedding = local_embeddings.get(speaker_name)
            if ref_embedding is not None:
                score = cosine_sim(
                    combined_embedding,
                    l2norm_vec(np.asarray(ref_embedding))
                )

                logger.info(f"  {speaker_name}: score={score:.3f}")

                if score > best_score:
                    best_score = score
                    best_label = speaker_name

    # Apply threshold to best match
    if best_score < threshold:
        logger.info(
            f"Best match '{best_label}' below threshold "
            f"({best_score:.3f} < {threshold})"
        )
        best_label = "No match"
        best_score = 0.0
    else:
        logger.info(f"✓ Best match: {best_label} (score={best_score:.3f})")

    # Clean up temp file
    if wav_path != local_media_path and os.path.exists(wav_path):
        try:
            os.remove(wav_path)
        except:
            pass

    return best_label, best_score, relabeled_utterances, presence


def map_worker_names_to_ids(
    local_embeddings: Dict[str, np.ndarray],
    worker_name_to_id: Dict[str, str]
) -> Dict[str, str]:
    """
    Map voice sample labels to worker IDs from database.
    Handles fuzzy matching on last names.

    Args:
        local_embeddings: Dict of worker labels from voice samples
        worker_name_to_id: Dict of legal names to IDs from database

    Returns:
        Dict mapping sample labels to worker IDs
    """
    label_to_worker_id = {}

    for label in local_embeddings.keys():
        # Try exact match first
        if label in worker_name_to_id:
            label_to_worker_id[label] = worker_name_to_id[label]
            logger.info(f"  Exact match: {label} -> {worker_name_to_id[label]}")
            continue

        # Try fuzzy match on last name
        label_last = label.split()[-1].lower()
        matched = False

        for db_name, worker_id in worker_name_to_id.items():
            db_last = db_name.split()[-1].lower()
            if label_last == db_last:
                label_to_worker_id[label] = worker_id
                logger.info(f"  Fuzzy match: {label} -> {worker_id} (via {db_name})")
                matched = True
                break

        if not matched:
            logger.warning(f"  No match for: {label}")

    return label_to_worker_id


def find_closest_speaker(
    utterance_embedding: np.ndarray,
    local_embeddings: Dict[str, np.ndarray],
    threshold: float = 0.2
) -> Tuple[str, float]:
    """
    Find the closest speaker for a single utterance embedding.

    Args:
        utterance_embedding: Embedding to match
        local_embeddings: Reference embeddings
        threshold: Minimum similarity threshold

    Returns:
        Tuple of (best_label, score)
    """
    best_label = "No match"
    best_score = 0.0

    for label, ref_embedding in local_embeddings.items():
        score = cosine_sim(
            utterance_embedding,
            l2norm_vec(np.asarray(ref_embedding, dtype=float))
        )

        if score > best_score:
            best_label = label
            best_score = score

    if best_score < threshold:
        return "No match", 0.0

    return best_label, best_score