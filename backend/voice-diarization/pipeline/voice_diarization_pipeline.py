#!/usr/bin/env python3
"""
Voice Diarization Pipeline
Clean implementation with proper resource management and error handling
"""

import os
import gc
import tempfile
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result from processing a single clip."""
    transaction_id: str
    worker_id: Optional[str]
    confidence: float
    success: bool
    error: Optional[str] = None


class VoiceDiarizationPipeline:
    """
    Main pipeline for voice diarization processing.
    Handles batch processing, GPU memory management, and error recovery.
    """

    def __init__(
        self,
        db_client,
        batch_size: int = 10,
        max_workers: int = 2,
        confidence_threshold: float = 0.75
    ):
        """
        Initialize the pipeline.

        Args:
            db_client: Database client instance
            batch_size: Number of clips to process per batch
            max_workers: Maximum concurrent processing threads
            confidence_threshold: Minimum confidence for worker match
        """
        self.db = db_client
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.confidence_threshold = confidence_threshold

        # Initialize components
        self.titanet_model = None
        self.gdrive_client = None
        self.worker_embeddings = {}

        logger.info(f"Initialized pipeline (batch_size={batch_size}, max_workers={max_workers})")

    def _initialize_titanet(self) -> bool:
        """Initialize TitaNet speaker verification model."""
        try:
            from nemo.collections.asr.models import EncDecSpeakerLabelModel

            logger.info("Loading TitaNet model...")

            # Load pre-trained TitaNet model
            self.titanet_model = EncDecSpeakerLabelModel.from_pretrained(
                model_name="titanet_large"
            )

            # Set to evaluation mode
            self.titanet_model.eval()

            # Move to GPU if available
            import torch
            if torch.cuda.is_available():
                self.titanet_model = self.titanet_model.cuda()
                logger.info("✅ TitaNet model loaded on GPU")
            else:
                logger.info("⚠️ TitaNet model loaded on CPU (slower)")

            return True

        except Exception as e:
            logger.error(f"Failed to initialize TitaNet: {e}")
            return False

    def _initialize_gdrive(self) -> bool:
        """Initialize Google Drive client."""
        try:
            from services.gdrive_client import GoogleDriveClient

            self.gdrive_client = GoogleDriveClient()
            logger.info("✅ Google Drive client initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Google Drive: {e}")
            return False

    def _build_worker_embeddings(self, location_name: str, samples_folder: Optional[str] = None) -> bool:
        """
        Build voice embeddings for workers from samples.

        Args:
            location_name: Name of the location
            samples_folder: Optional custom folder name for samples

        Returns:
            Success boolean
        """
        try:
            # Default samples folder
            if not samples_folder:
                samples_folder = f"{location_name} Voice Samples"

            logger.info(f"Building worker embeddings from '{samples_folder}'")

            # Get workers from database
            workers = self.db.get_workers()
            if not workers:
                logger.warning("No workers found in database")
                return False

            # Download and process voice samples
            for worker in workers:
                worker_name = worker['legal_name']
                worker_id = worker['id']

                try:
                    # Find voice sample for worker
                    sample_path = self._download_worker_sample(
                        samples_folder,
                        worker_name
                    )

                    if sample_path:
                        # Generate embedding
                        embedding = self._generate_embedding(sample_path)
                        if embedding is not None:
                            self.worker_embeddings[worker_id] = {
                                'name': worker_name,
                                'embedding': embedding
                            }
                            logger.info(f"✓ Generated embedding for {worker_name}")

                        # Clean up temp file
                        Path(sample_path).unlink(missing_ok=True)
                    else:
                        logger.warning(f"No sample found for {worker_name}")

                except Exception as e:
                    logger.error(f"Error processing {worker_name}: {e}")

            logger.info(f"Built embeddings for {len(self.worker_embeddings)} workers")
            return len(self.worker_embeddings) > 0

        except Exception as e:
            logger.error(f"Failed to build worker embeddings: {e}")
            return False

    def _download_worker_sample(self, folder: str, worker_name: str) -> Optional[str]:
        """Download voice sample for a worker."""
        try:
            # Search for audio file with worker's name
            files = self.gdrive_client.list_files_in_folder(folder)

            for file in files:
                if worker_name.lower() in file['name'].lower():
                    # Download to temp file
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                        self.gdrive_client.download_file(file['id'], tmp.name)
                        return tmp.name

            return None

        except Exception as e:
            logger.error(f"Error downloading sample for {worker_name}: {e}")
            return None

    def _generate_embedding(self, audio_path: str) -> Optional[np.ndarray]:
        """Generate voice embedding from audio file."""
        try:
            import torch
            import torchaudio

            # Load and preprocess audio
            waveform, sample_rate = torchaudio.load(audio_path)

            # Resample to 16kHz if needed
            if sample_rate != 16000:
                resampler = torchaudio.transforms.Resample(sample_rate, 16000)
                waveform = resampler(waveform)

            # Convert to mono
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)

            # Move to GPU if available
            if torch.cuda.is_available():
                waveform = waveform.cuda()

            # Generate embedding
            with torch.no_grad():
                embedding = self.titanet_model.infer_segment(waveform)

            # Convert to numpy
            embedding = embedding.cpu().numpy()

            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    def _process_clip_batch(self, clips: List[Dict[str, Any]]) -> List[ProcessingResult]:
        """
        Process a batch of clips.

        Args:
            clips: List of clip records

        Returns:
            List of processing results
        """
        results = []

        for clip in clips:
            result = self._process_single_clip(clip)
            results.append(result)

            # Clear GPU memory periodically
            if len(results) % 5 == 0:
                self._clear_gpu_memory()

        return results

    def _process_single_clip(self, clip: Dict[str, Any]) -> ProcessingResult:
        """Process a single transaction clip."""
        transaction_id = clip['transaction_id']

        try:
            # Download clip audio
            audio_path = self._download_clip(clip)
            if not audio_path:
                return ProcessingResult(
                    transaction_id=transaction_id,
                    worker_id=None,
                    confidence=0.0,
                    success=False,
                    error="Failed to download audio"
                )

            # Generate embedding for clip
            clip_embedding = self._generate_embedding(audio_path)

            # Clean up temp file
            Path(audio_path).unlink(missing_ok=True)

            if clip_embedding is None:
                return ProcessingResult(
                    transaction_id=transaction_id,
                    worker_id=None,
                    confidence=0.0,
                    success=False,
                    error="Failed to generate embedding"
                )

            # Match against worker embeddings
            best_match, confidence = self._match_worker(clip_embedding)

            # Apply confidence threshold
            if confidence >= self.confidence_threshold:
                worker_id = best_match
            else:
                worker_id = None

            return ProcessingResult(
                transaction_id=transaction_id,
                worker_id=worker_id,
                confidence=confidence,
                success=True
            )

        except Exception as e:
            logger.error(f"Error processing clip {transaction_id}: {e}")
            return ProcessingResult(
                transaction_id=transaction_id,
                worker_id=None,
                confidence=0.0,
                success=False,
                error=str(e)
            )

    def _download_clip(self, clip: Dict[str, Any]) -> Optional[str]:
        """Download clip from S3 or Google Drive."""
        try:
            # Check if we have S3 info
            if clip.get('audio_s3_bucket') and clip.get('audio_s3_key'):
                # Download from S3
                return self._download_from_s3(
                    clip['audio_s3_bucket'],
                    clip['audio_s3_key']
                )
            else:
                # Try Google Drive fallback
                return self._download_from_gdrive(clip)

        except Exception as e:
            logger.error(f"Error downloading clip: {e}")
            return None

    def _download_from_s3(self, bucket: str, key: str) -> Optional[str]:
        """Download audio from S3."""
        try:
            import boto3

            s3 = boto3.client('s3')

            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                s3.download_file(bucket, key, tmp.name)
                return tmp.name

        except Exception as e:
            logger.error(f"Error downloading from S3: {e}")
            return None

    def _download_from_gdrive(self, clip: Dict[str, Any]) -> Optional[str]:
        """Download audio from Google Drive."""
        # Implementation depends on your Google Drive structure
        # This is a placeholder
        return None

    def _match_worker(self, clip_embedding: np.ndarray) -> Tuple[Optional[str], float]:
        """
        Match clip embedding against worker embeddings.

        Args:
            clip_embedding: Voice embedding from clip

        Returns:
            Tuple of (worker_id, confidence_score)
        """
        try:
            if not self.worker_embeddings:
                return None, 0.0

            best_match = None
            best_score = 0.0

            # Compare against each worker
            for worker_id, worker_data in self.worker_embeddings.items():
                # Calculate cosine similarity
                score = self._cosine_similarity(
                    clip_embedding,
                    worker_data['embedding']
                )

                if score > best_score:
                    best_score = score
                    best_match = worker_id

            return best_match, best_score

        except Exception as e:
            logger.error(f"Error matching worker: {e}")
            return None, 0.0

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings."""
        try:
            # Flatten arrays
            a = a.flatten()
            b = b.flatten()

            # Calculate cosine similarity
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)

            if norm_a == 0 or norm_b == 0:
                return 0.0

            similarity = dot_product / (norm_a * norm_b)

            # Ensure in range [0, 1]
            return max(0.0, min(1.0, (similarity + 1) / 2))

        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0

    def _clear_gpu_memory(self):
        """Clear GPU memory cache."""
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                gc.collect()
        except:
            pass

    def process(self, location_id: str, date: str) -> Dict[str, Any]:
        """
        Main processing method.

        Args:
            location_id: Location UUID
            date: Date string (YYYY-MM-DD)

        Returns:
            Processing results dictionary
        """
        results = {
            'processed': 0,
            'updated': 0,
            'no_match': 0,
            'failures': 0,
            'errors': []
        }

        try:
            # Initialize components
            if not self._initialize_titanet():
                raise ValueError("Failed to initialize TitaNet model")

            if not self._initialize_gdrive():
                raise ValueError("Failed to initialize Google Drive")

            # Get location name
            location_name = self.db.get_location_name(location_id)
            if not location_name:
                raise ValueError(f"Location {location_id} not found")

            # Build worker embeddings
            if not self._build_worker_embeddings(location_name):
                logger.warning("No worker embeddings built, continuing anyway")

            # Get transactions for the date
            transactions = self.db.get_transactions_for_date(location_id, date)
            total_clips = len(transactions)
            logger.info(f"Processing {total_clips} transaction clips")

            # Process in batches
            for i in range(0, total_clips, self.batch_size):
                batch = transactions[i:i + self.batch_size]
                logger.info(f"Processing batch {i//self.batch_size + 1} ({len(batch)} clips)")

                # Process batch
                batch_results = self._process_clip_batch(batch)

                # Update database
                for result in batch_results:
                    results['processed'] += 1

                    if result.success:
                        # Update transaction
                        success = self.db.update_transaction_worker(
                            result.transaction_id,
                            result.worker_id,
                            result.confidence
                        )

                        if success:
                            if result.worker_id:
                                results['updated'] += 1
                            else:
                                results['no_match'] += 1
                        else:
                            results['failures'] += 1
                    else:
                        results['failures'] += 1
                        if result.error:
                            results['errors'].append(result.error)

                # Clear GPU memory after each batch
                self._clear_gpu_memory()

                # Log progress
                logger.info(f"Progress: {results['processed']}/{total_clips} clips")

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            results['errors'].append(str(e))

        finally:
            # Clean up
            self._clear_gpu_memory()

        return results