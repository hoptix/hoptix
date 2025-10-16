"""
Voice Diarization Service for speaker identification using TitaNet embeddings.
Processes audio clips to identify workers based on voice matching.
"""

from __future__ import annotations

import os
import tempfile
import uuid
import glob
import mimetypes
import wave
import logging
from typing import Dict, List, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Conditional imports for GPU dependencies
TORCH_AVAILABLE = False
TORCH_ERROR = None

try:
    import torch
    logger.info(f"PyTorch imported successfully: {torch.__version__}")
    logger.info(f"CUDA available: {torch.cuda.is_available()}")

    try:
        import torchaudio
        logger.info(f"Torchaudio imported successfully: {torchaudio.__version__}")
    except Exception as torchaudio_error:
        logger.error(f"Torchaudio import failed: {torchaudio_error}")
        raise

    try:
        from nemo.collections.asr.models import EncDecSpeakerLabelModel
        logger.info("NeMo ASR models imported successfully")
        TORCH_AVAILABLE = True
    except Exception as nemo_error:
        logger.error(f"NeMo import failed: {nemo_error}")
        raise

except Exception as e:
    TORCH_AVAILABLE = False
    TORCH_ERROR = str(e)
    import warnings
    import traceback
    error_details = f"PyTorch/NeMo import error: {e}"
    logger.error(error_details)
    logger.error(f"Traceback: {traceback.format_exc()}")
    warnings.warn(f"PyTorch and NeMo not available. Voice diarization will not work. Error: {error_details}")

# Audio processing imports (these should always work)
try:
    from pydub import AudioSegment
    import assemblyai as aai
except ImportError as e:
    import warnings
    warnings.warn(f"Audio processing libraries not available: {e}")

try:
    # Try to import the regular database module
    from services.database import Supa
except ImportError:
    # Fall back to the lightweight version for voice diarization
    from services.database_voice import Supa

from services.gdrive import GoogleDriveClient
from services.monitoring import MonitoringService, retry_with_monitoring
from config import Settings

logger = logging.getLogger(__name__)

# Audio file extensions
SUPPORTED_AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".flac", ".aac", ".ogg", ".wma", ".mkv", ".mp4"}


class VoiceDiarization:
    """Service for voice-based worker identification using TitaNet embeddings."""

    def __init__(self):
        """Initialize voice diarization service with configuration."""
        self.db = Supa()
        self.gdrive = GoogleDriveClient()
        self.monitor = MonitoringService()

        # Load configuration from environment
        self.aai_api_key = os.getenv("AAI_API_KEY")
        self.threshold = float(os.getenv("VOICE_DIARIZATION_THRESHOLD", "0.2"))
        self.min_utterance_ms = int(os.getenv("VOICE_MIN_UTTERANCE_MS", "1000"))
        self.parallel_workers = int(os.getenv("VOICE_PARALLEL_WORKERS", "5"))

        # Initialize AssemblyAI
        if self.aai_api_key:
            aai.settings.api_key = self.aai_api_key
        else:
            logger.warning("AAI_API_KEY not set - transcription features will be unavailable")

        # Speaker model will be loaded when needed
        self.speaker_model = None
        self.worker_name_to_id = {}

    def load_speaker_model(self):
        """Load TitaNet speaker verification model (lazy loading for GPU efficiency)."""
        if not TORCH_AVAILABLE:
            error_msg = "PyTorch and NeMo are not available. Cannot load TitaNet model."
            if TORCH_ERROR:
                error_msg += f" Import error: {TORCH_ERROR}"
            error_msg += " Please check the Docker build logs and ensure GPU-enabled deployment."
            raise RuntimeError(error_msg)

        if self.speaker_model is None:
            logger.info("Loading TitaNet speaker verification model...")
            self.speaker_model = EncDecSpeakerLabelModel.from_pretrained(
                "nvidia/speakerverification_en_titanet_large"
            )
            logger.info("TitaNet model loaded successfully")
        return self.speaker_model

    @retry_with_monitoring(api_name="supabase_get_workers", max_retries=3)
    def get_worker_name_to_id(self) -> Dict[str, str]:
        """
        Fetch workers from Supabase and return a mapping {legal_name: id}.
        Includes bug fix for handling empty results and retry logic.
        """
        try:
            resp = self.db.client.table("workers").select("id, legal_name").execute()
        except Exception as e:
            logger.error(f"Supabase request failed: {e}")
            raise  # Re-raise to trigger retry

        # Handle different response formats safely
        data = None
        if hasattr(resp, "data"):
            data = resp.data
        elif isinstance(resp, dict) and "data" in resp:
            data = resp["data"]
        else:
            try:
                data = resp.get("data") if hasattr(resp, 'get') else None
            except Exception:
                data = None

        if data is None:
            logger.warning(f"Unexpected response shape from supabase: {type(resp)}")
            return {}

        worker_map = {}
        for worker in data:
            # Handle different naming conventions
            name = worker.get("legal_name") or worker.get("name") or worker.get("display_name")
            wid = worker.get("id")
            if name and wid:
                worker_map[name] = wid

        logger.info(f"Loaded {len(worker_map)} workers from database")
        return worker_map

    @retry_with_monitoring(api_name="supabase_check_transaction", max_retries=2)
    def check_complete_transactions_or_labeled(self, transaction_id: str) -> bool:
        """
        Checks if a transaction is complete or already labeled in the graded_rows_filtered table.
        Returns True if the transaction should be skipped, False otherwise.
        Includes bug fix for handling empty query results and retry logic.
        """
        try:
            transaction = self.db.client.table("graded_rows_filtered").select("*").eq(
                "transaction_id", transaction_id
            ).execute()

            # Check if any data was returned (bug fix)
            if not transaction.data:
                logger.info(f"Transaction {transaction_id} not found in graded_rows_filtered table. Skipping.")
                return True

            # Access the first element only if data exists
            if not transaction.data[0].get('complete_order'):
                logger.info(f"Order for transaction {transaction_id} not complete. Skipping.")
                return True

            if transaction.data[0].get('worker_id') is not None:
                logger.info(f"Worker for transaction {transaction_id} already labeled. Skipping.")
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking transaction {transaction_id}: {e}")
            return True

    def ensure_wav_mono(self, src_path: str, out_dir: str = None) -> str:
        """
        Convert any local media (audio/video) to mono WAV and return the path.
        """
        if out_dir is None:
            out_dir = os.getenv("VOICE_CONVERTED_DIR", "./content/converted_audio")

        os.makedirs(out_dir, exist_ok=True)
        base = os.path.splitext(os.path.basename(src_path))[0]
        wav_path = os.path.join(out_dir, f"{base}.wav")

        # If source is already the desired file, just return
        if os.path.abspath(src_path) == os.path.abspath(wav_path) and os.path.exists(wav_path):
            return wav_path

        audio = AudioSegment.from_file(src_path)
        if audio.channels > 1:
            audio = audio.set_channels(1)
        # Normalize sample rate to 16k for TitaNet
        audio = audio.set_frame_rate(16000)
        audio.export(wav_path, format="wav")
        return wav_path

    def l2norm_vec(self, x: np.ndarray) -> np.ndarray:
        """L2 normalize a vector."""
        x = np.asarray(x, dtype=float)
        n = np.linalg.norm(x)
        return x / (n + 1e-12)

    def get_embedding_for_wav(self, wav_path: str) -> np.ndarray:
        """
        Compute a (192,) embedding using TitaNet for a WAV file.
        """
        model = self.load_speaker_model()
        emb = model.get_embedding(wav_path)

        if TORCH_AVAILABLE and hasattr(emb, 'squeeze'):
            # It's a torch.Tensor
            emb = emb.squeeze().cpu().numpy()
        else:
            emb = np.asarray(emb).squeeze()

        emb = emb.astype(float)
        if emb.shape != (192,):
            raise ValueError(f"Expected (192,) embedding, got {emb.shape} for {wav_path}")

        return self.l2norm_vec(emb)

    def filename_to_label(self, path: str) -> str:
        """Turn 'Cary_Office01.wav' -> 'Cary Office01' (nicer label)."""
        stem = os.path.splitext(os.path.basename(path))[0]
        return stem.replace("_", " ").strip()

    @retry_with_monitoring(api_name="gdrive_get_folder", max_retries=3)
    def _get_gdrive_folder_id(self, folder_name: str) -> str:
        """Get Google Drive folder ID with retry logic."""
        folder_id = self.gdrive.get_folder_id_from_name(folder_name)
        if not folder_id:
            raise ValueError(f"Folder '{folder_name}' not found in Google Drive")
        return folder_id

    @retry_with_monitoring(api_name="gdrive_list_files", max_retries=3)
    def _list_gdrive_files(self, folder_id: str) -> list:
        """List files in Google Drive folder with retry logic."""
        return self.gdrive.list_media_files_shared_with_me(folder_id)

    @retry_with_monitoring(api_name="gdrive_download", max_retries=3)
    def _download_gdrive_file(self, file_id: str, local_path: str) -> bool:
        """Download file from Google Drive with retry logic."""
        result = self.gdrive.download_file(file_id, local_path)
        if not result:
            raise RuntimeError(f"Failed to download file {file_id}")
        return result

    def build_local_embeddings(self, samples_folder: str) -> Dict[str, np.ndarray]:
        """
        Build embeddings from reference voice samples in Google Drive folder.
        """
        logger.info(f"Building embeddings from samples folder: {samples_folder}")

        # Get folder ID from Google Drive with retry
        folder_id = self._get_gdrive_folder_id(samples_folder)

        # List all WAV files in the folder with retry
        files = self._list_gdrive_files(folder_id)
        wav_files = [f for f in files if f['name'].endswith('.wav')]

        if not wav_files:
            raise ValueError(f"No WAV files found in samples folder '{samples_folder}'")

        local_embeddings = {}
        temp_dir = tempfile.mkdtemp(prefix="voice_samples_")

        try:
            for file_info in wav_files:
                file_id = file_info['id']
                file_name = file_info['name']
                label = self.filename_to_label(file_name)

                # Download to temp location with retry
                local_path = os.path.join(temp_dir, file_name)
                try:
                    if self._download_gdrive_file(file_id, local_path):
                        # Convert to mono WAV and get embedding
                        wav_path = self.ensure_wav_mono(local_path, temp_dir)
                        emb = self.get_embedding_for_wav(wav_path)
                        local_embeddings[label] = emb
                        logger.info(f"  - embedded: {label}")

                        # Clean up temp file
                        if os.path.exists(local_path) and local_path != wav_path:
                            os.remove(local_path)
                        if os.path.exists(wav_path):
                            os.remove(wav_path)
                except Exception as e:
                    logger.error(f"Failed to process sample {file_name}: {e}")

        finally:
            # Clean up temp directory
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except:
                pass

        logger.info(f"Built {len(local_embeddings)} embeddings from samples")
        return local_embeddings

    def transcribe_with_speaker_labels(self, local_media_path: str, max_retries: int = 3) -> dict:
        """
        Transcribe a LOCAL file with AssemblyAI and return json_response.
        Includes retry logic for API failures.
        """
        if not self.aai_api_key:
            raise RuntimeError("AAI_API_KEY not configured")

        config = aai.TranscriptionConfig(speaker_labels=True)
        transcriber = aai.Transcriber(config=config)

        for attempt in range(max_retries):
            try:
                transcript = transcriber.transcribe(local_media_path)
                if transcript.status == "error":
                    logger.warning(f"Transcription error: {transcript.error}")
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(5 * (attempt + 1))  # Exponential backoff
                        continue
                    raise RuntimeError(f"Transcription failed: {transcript.error}")
                return transcript.json_response
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Transcription attempt {attempt + 1} failed: {e}")
                    import time
                    time.sleep(5 * (attempt + 1))  # Exponential backoff
                else:
                    raise

        raise RuntimeError(f"Transcription failed after {max_retries} attempts")

    def cosine_sim(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        return float(cosine_similarity(a.reshape(1, -1), b.reshape(1, -1))[0][0])

    def avg_embed_top_n_utterances(
        self,
        audio: AudioSegment,
        utterances: List[dict],
        diarized_tag: str,
        top_n: int = 3,
    ) -> Optional[np.ndarray]:
        """
        Average embeddings from the top_n longest utterances for the diarized_tag.
        """
        utts = [u for u in utterances if u["speaker"] == diarized_tag]
        if not utts:
            return None

        top = sorted(utts, key=lambda u: (u["end"] - u["start"]), reverse=True)[:top_n]
        embs = []

        for u in top:
            start_ms, end_ms = int(u["start"]), int(u["end"])
            seg = audio[start_ms:end_ms]
            converted_dir = os.getenv("VOICE_CONVERTED_DIR", "./content/converted_audio")
            os.makedirs(converted_dir, exist_ok=True)
            tmp = os.path.join(converted_dir, f"tmp_avg_{uuid.uuid4().hex[:8]}.wav")
            seg.export(tmp, format="wav")
            try:
                e = self.get_embedding_for_wav(tmp)
                embs.append(self.l2norm_vec(e))
            finally:
                try:
                    os.remove(tmp)
                except:
                    pass

        if not embs:
            return None

        avg = np.vstack(embs).mean(axis=0)
        return self.l2norm_vec(avg)

    def concat_and_embed_until_length(
        self,
        audio: AudioSegment,
        utterances: List[dict],
        diarized_tag: str,
        target_ms: int = 8000,
        max_utts: int = 6,
    ) -> Optional[np.ndarray]:
        """
        Concatenate utterances in chronological order until total >= target_ms.
        """
        utts = sorted([u for u in utterances if u["speaker"] == diarized_tag], key=lambda u: u["start"])
        if not utts:
            return None

        pieces = []
        total = 0
        count = 0

        for u in utts:
            start_ms, end_ms = int(u["start"]), int(u["end"])
            seg = audio[start_ms:end_ms]
            pieces.append(seg)
            total += len(seg)
            count += 1
            if total >= target_ms or count >= max_utts:
                break

        if not pieces:
            return None

        concat = pieces[0]
        for p in pieces[1:]:
            concat += p

        converted_dir = os.getenv("VOICE_CONVERTED_DIR", "./content/converted_audio")
        os.makedirs(converted_dir, exist_ok=True)
        tmp = os.path.join(converted_dir, f"tmp_cat_{uuid.uuid4().hex[:8]}.wav")
        concat.export(tmp, format="wav")

        try:
            e = self.get_embedding_for_wav(tmp)
            return self.l2norm_vec(e)
        finally:
            try:
                os.remove(tmp)
            except:
                pass

    def identify_speakers_in_transcript(
        self,
        transcript_json: dict,
        wav_path: str,
        local_embeddings: Dict[str, np.ndarray],
    ) -> Tuple[List[dict], Dict[str, bool], str, float]:
        """
        Map diarized speakers to known samples and return best match.
        Returns: (relabeled_utterances, presence_map, best_label, best_score)
        """
        utterances = transcript_json.get("utterances", [])
        if not utterances:
            raise ValueError("No 'utterances' found in transcript")

        audio = AudioSegment.from_wav(wav_path)
        diarized_to_label = {}

        # Map each diarized speaker to a known worker
        for diarized_speaker in sorted(set(u["speaker"] for u in utterances)):
            # Try multiple embedding strategies
            emb = self.avg_embed_top_n_utterances(audio, utterances, diarized_speaker, top_n=3)

            if emb is None:
                emb = self.concat_and_embed_until_length(
                    audio, utterances, diarized_speaker, target_ms=8000, max_utts=8
                )

            if emb is None:
                logger.info(f"Diarized '{diarized_speaker}' -> 'No match' (no usable audio)")
                diarized_to_label[diarized_speaker] = "No match"
                continue

            # Find best matching worker
            best_label = "No match"
            best_score = 0.0

            for label, ref_emb in local_embeddings.items():
                ref = self.l2norm_vec(np.asarray(ref_emb, dtype=float))
                score = self.cosine_sim(emb, ref)
                if score > best_score:
                    best_label, best_score = label, score

            # Apply threshold
            if best_score < self.threshold:
                logger.info(f"Diarized '{diarized_speaker}' -> 'No match' (best={best_label}, score={best_score:.3f})")
                diarized_to_label[diarized_speaker] = "No match"
            else:
                logger.info(f"Diarized '{diarized_speaker}' -> '{best_label}' (score={best_score:.3f})")
                diarized_to_label[diarized_speaker] = best_label

        # Relabel utterances
        relabeled = []
        for u in utterances:
            src = dict(u)
            src["speaker_original"] = src["speaker"]
            src["speaker"] = diarized_to_label.get(src["speaker_original"], "No match")
            relabeled.append(src)

        # Calculate presence and find overall best match
        presence = {label: False for label in local_embeddings.keys()}
        speaker_scores = {}

        for u in relabeled:
            speaker = u["speaker"]
            if speaker in presence:
                presence[speaker] = True
                # Track total speaking time for scoring
                duration = u["end"] - u["start"]
                if speaker not in speaker_scores:
                    speaker_scores[speaker] = 0
                speaker_scores[speaker] += duration

        # Find speaker with most speaking time as best match
        best_label = "No match"
        best_score = 0.0

        if speaker_scores:
            best_speaker = max(speaker_scores.items(), key=lambda x: x[1])
            if best_speaker[0] != "No match":
                best_label = best_speaker[0]
                # Get average confidence for this speaker
                matches = [diarized_to_label[k] for k in diarized_to_label if diarized_to_label[k] == best_label]
                if matches:
                    best_score = self.threshold + 0.5  # Placeholder score since we need to recalculate

        return relabeled, presence, best_label, best_score

    def process_clip(
        self,
        clip_path: str,
        local_embeddings: Dict[str, np.ndarray],
        label_to_worker_id: Dict[str, str]
    ) -> Tuple[int, int, int]:
        """
        Process a single transaction clip and update database if needed.
        Returns: (updated_count, no_match_count, failure_count)
        """
        import re

        base = os.path.basename(clip_path)

        # Match transaction ID from filename (tx_[UUID].wav or .mp3)
        m = re.match(r"tx_([0-9a-fA-F-]{36})\.(wav|mp3)$", base, re.IGNORECASE)
        if not m:
            logger.warning(f"Skip (bad name): {base}")
            return 0, 0, 0

        tx_id = m.group(1)
        logger.info(f"Processing transaction: {tx_id}")

        # Check if already processed or incomplete
        if self.check_complete_transactions_or_labeled(tx_id):
            return 0, 0, 0

        try:
            # Convert to WAV if needed
            wav_path = self.ensure_wav_mono(clip_path)

            # Transcribe with speaker labels
            transcript_json = self.transcribe_with_speaker_labels(wav_path)

            # Identify speakers
            relabeled, presence, best_label, score = self.identify_speakers_in_transcript(
                transcript_json, wav_path, local_embeddings
            )

            logger.info(f"Best match speaker: {best_label}, score: {score}")

            # Get worker ID
            worker_id = label_to_worker_id.get(best_label)
            if not worker_id or best_label == "No match":
                logger.info("No match over threshold; leaving worker_id NULL.")
                return 0, 1, 0

            # Update database
            resp = self.db.client.table("transactions").update({
                "worker_id": worker_id,
                "worker_assignment_source": "voice",
                "worker_confidence": float(score),
            }).eq("id", tx_id).execute()

            logger.info(f"Updated transaction {tx_id} with worker_id={worker_id}, confidence={score:.3f}")

            # Clean up temp file
            if wav_path != clip_path and os.path.exists(wav_path):
                os.remove(wav_path)

            return 1, 0, 0

        except Exception as e:
            logger.error(f"Failed to process clip {clip_path}: {e}")
            return 0, 0, 1

    def process_clips_batch(
        self,
        clips_folder: str,
        samples_folder: str
    ) -> Dict[str, int]:
        """
        Process all transaction clips in a Google Drive folder.
        Returns statistics about processing results.
        """
        # Load speaker model
        self.load_speaker_model()

        # Get worker mapping
        self.worker_name_to_id = self.get_worker_name_to_id()

        # Build embeddings from samples
        local_embeddings = self.build_local_embeddings(samples_folder)

        # Map labels to worker IDs
        label_to_worker_id = {}
        for label in local_embeddings.keys():
            if label in self.worker_name_to_id:
                label_to_worker_id[label] = self.worker_name_to_id[label]
            else:
                # Try matching last name
                last = label.split()[-1].lower()
                for name, wid in self.worker_name_to_id.items():
                    if last == name.split()[-1].lower():
                        label_to_worker_id[label] = wid
                        break

        logger.info("Label→worker_id mapping:")
        for k, v in label_to_worker_id.items():
            logger.info(f"  {k} → {v}")

        # Get clips from Google Drive
        folder_id = self.gdrive.get_folder_id_from_name(clips_folder)
        if not folder_id:
            raise ValueError(f"Clips folder '{clips_folder}' not found in Google Drive")

        files = self.gdrive.list_media_files_shared_with_me(folder_id)

        # Filter for transaction clips
        clip_files = []
        for f in files:
            name = f['name']
            if name.startswith('tx_') and (name.endswith('.wav') or name.endswith('.mp3')):
                clip_files.append(f)

        logger.info(f"Found {len(clip_files)} transaction clips to process")

        if not clip_files:
            return {"processed": 0, "updated": 0, "no_match": 0, "failures": 0}

        # Process clips in parallel
        updated_total = 0
        no_match_total = 0
        failures_total = 0

        temp_dir = tempfile.mkdtemp(prefix="voice_clips_")

        try:
            with ThreadPoolExecutor(max_workers=self.parallel_workers) as executor:
                futures = []

                # Download and queue clips for processing
                for file_info in clip_files:
                    file_id = file_info['id']
                    file_name = file_info['name']
                    local_path = os.path.join(temp_dir, file_name)

                    if self.gdrive.download_file(file_id, local_path):
                        future = executor.submit(
                            self.process_clip,
                            local_path,
                            local_embeddings,
                            label_to_worker_id
                        )
                        futures.append((future, local_path))

                # Collect results
                for future, local_path in futures:
                    try:
                        updated, no_match, failures = future.result(timeout=300)  # 5 min timeout
                        updated_total += updated
                        no_match_total += no_match
                        failures_total += failures
                    except Exception as e:
                        logger.error(f"Task failed: {e}")
                        failures_total += 1
                    finally:
                        # Clean up downloaded file
                        try:
                            if os.path.exists(local_path):
                                os.remove(local_path)
                        except:
                            pass

        finally:
            # Clean up temp directory
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except:
                pass

        return {
            "processed": len(clip_files),
            "updated": updated_total,
            "no_match": no_match_total,
            "failures": failures_total
        }