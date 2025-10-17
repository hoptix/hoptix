#!/usr/bin/env python3
"""
Voice Diarization Pipeline
Uses AssemblyAI for transcription and speaker diarization
Matches speakers to workers using TitaNet embeddings
"""

import os
import re
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
    worker_name: Optional[str]
    confidence: float
    success: bool
    error: Optional[str] = None
    transcript: Optional[Dict[str, Any]] = None


class VoiceDiarizationPipeline:
    """
    Main pipeline for voice diarization processing.
    Uses AssemblyAI for diarization and TitaNet for speaker verification.
    """

    def __init__(
        self,
        db_client,
        gdrive_client=None,
        batch_size: int = 10,
        max_workers: int = 5,
        confidence_threshold: float = 0.2,
        min_utterance_ms: int = 1000
    ):
        """
        Initialize the pipeline.

        Args:
            db_client: Database client instance
            gdrive_client: Optional Google Drive client
            batch_size: Number of clips to process per batch
            max_workers: Maximum concurrent processing threads
            confidence_threshold: Minimum confidence for worker match
            min_utterance_ms: Minimum utterance length for robust embeddings
        """
        self.db = db_client
        self.gdrive = gdrive_client
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.confidence_threshold = confidence_threshold
        self.min_utterance_ms = min_utterance_ms

        # Initialize components
        self.titanet_model = None
        self.worker_embeddings = {}
        self.label_to_worker_id = {}

        logger.info(
            f"Initialized pipeline (batch_size={batch_size}, "
            f"max_workers={max_workers}, threshold={confidence_threshold})"
        )

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
        """Initialize or verify Google Drive client."""
        if self.gdrive:
            logger.info("✅ Using provided Google Drive client")
            return True

        try:
            from services.gdrive_client import GoogleDriveClient
            self.gdrive = GoogleDriveClient()
            logger.info("✅ Google Drive client initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Google Drive: {e}")
            return False

    def _build_worker_embeddings(self, location_name: str) -> bool:
        """
        Build voice embeddings for workers from Google Drive samples.

        Args:
            location_name: Name of the location

        Returns:
            Success boolean
        """
        from services.speaker_matcher import build_local_embeddings

        try:
            logger.info(f"Building worker embeddings for location: {location_name}")

            # Download voice samples to temp directory
            temp_dir = tempfile.mkdtemp(prefix="voice_samples_")
            sample_paths = self.gdrive.download_voice_samples(location_name, temp_dir)

            if not sample_paths:
                logger.warning(f"No voice samples found for {location_name}")
                return False

            # Build embeddings
            self.worker_embeddings = build_local_embeddings(
                temp_dir,
                self.titanet_model
            )

            # Clean up temp files
            import shutil
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

            logger.info(f"Built embeddings for {len(self.worker_embeddings)} workers")
            return len(self.worker_embeddings) > 0

        except Exception as e:
            logger.error(f"Failed to build worker embeddings: {e}")
            return False

    def _map_worker_names_to_ids(self) -> None:
        """Map worker names from voice samples to database IDs."""
        from services.speaker_matcher import map_worker_names_to_ids

        # Get workers from database
        workers = self.db.get_workers()
        if not workers:
            logger.warning("No workers found in database")
            return

        # Build name to ID mapping
        worker_name_to_id = {}
        for worker in workers:
            name = worker.get('legal_name')
            wid = worker.get('id')
            if name and wid:
                worker_name_to_id[name] = wid

        # Map voice sample labels to worker IDs
        self.label_to_worker_id = map_worker_names_to_ids(
            self.worker_embeddings,
            worker_name_to_id
        )

        logger.info(f"Mapped {len(self.label_to_worker_id)} voice samples to worker IDs")

    def _process_single_clip(
        self,
        clip_path: str,
        transaction_id: str
    ) -> ProcessingResult:
        """
        Process a single transaction clip using AssemblyAI diarization.

        Args:
            clip_path: Path to audio clip
            transaction_id: Transaction UUID

        Returns:
            ProcessingResult with worker assignment
        """
        from services.speaker_matcher import run_pipeline_on_media_best_match

        try:
            logger.info(f"Processing transaction {transaction_id}")

            # Run diarization and matching pipeline
            best_label, best_score, relabeled_utterances, presence = run_pipeline_on_media_best_match(
                local_media_path=clip_path,
                speaker_model=self.titanet_model,
                local_embeddings=self.worker_embeddings,
                threshold=self.confidence_threshold,
                min_utterance_ms=self.min_utterance_ms
            )

            # Map label to worker ID
            worker_id = self.label_to_worker_id.get(best_label)

            if not worker_id or best_label == "No match":
                logger.info(
                    f"Transaction {transaction_id}: No match "
                    f"(best={best_label}, score={best_score:.3f})"
                )
                return ProcessingResult(
                    transaction_id=transaction_id,
                    worker_id=None,
                    worker_name=None,
                    confidence=best_score,
                    success=True,
                    transcript={"utterances": relabeled_utterances}
                )

            logger.info(
                f"Transaction {transaction_id}: Matched {best_label} "
                f"(worker_id={worker_id}, confidence={best_score:.3f})"
            )

            return ProcessingResult(
                transaction_id=transaction_id,
                worker_id=worker_id,
                worker_name=best_label,
                confidence=best_score,
                success=True,
                transcript={"utterances": relabeled_utterances}
            )

        except Exception as e:
            logger.error(f"Error processing clip {transaction_id}: {e}")
            return ProcessingResult(
                transaction_id=transaction_id,
                worker_id=None,
                worker_name=None,
                confidence=0.0,
                success=False,
                error=str(e)
            )

    def _process_clip_from_drive(
        self,
        clip_metadata: Dict[str, Any]
    ) -> ProcessingResult:
        """
        Process a clip from Google Drive.

        Args:
            clip_metadata: Drive file metadata

        Returns:
            ProcessingResult
        """
        import re

        # Extract transaction ID from filename
        filename = clip_metadata.get('name', '')
        match = re.match(r'^tx_([0-9a-fA-F-]{36})\.(wav|mp3|m4a)$', filename, re.IGNORECASE)

        if not match:
            logger.warning(f"Invalid clip filename: {filename}")
            return ProcessingResult(
                transaction_id="unknown",
                worker_id=None,
                worker_name=None,
                confidence=0.0,
                success=False,
                error=f"Invalid filename pattern: {filename}"
            )

        transaction_id = match.group(1)

        # Check if should skip
        if self.db.should_skip_transaction(transaction_id):
            logger.info(f"Skipping transaction {transaction_id} (complete or already labeled)")
            return ProcessingResult(
                transaction_id=transaction_id,
                worker_id=None,
                worker_name=None,
                confidence=0.0,
                success=False,
                error="Transaction already processed or incomplete"
            )

        # Download clip to temp file
        temp_file = os.path.join(
            tempfile.gettempdir(),
            f"clip_{transaction_id}.wav"
        )

        try:
            if not self.gdrive.download_file(clip_metadata['id'], temp_file):
                raise Exception("Failed to download clip")

            # Process the clip
            result = self._process_single_clip(temp_file, transaction_id)

            return result

        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

    def _process_batch_parallel(
        self,
        clips: List[Dict[str, Any]]
    ) -> List[ProcessingResult]:
        """
        Process a batch of clips in parallel.

        Args:
            clips: List of clip metadata from Google Drive

        Returns:
            List of processing results
        """
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all clips for processing
            futures = {
                executor.submit(self._process_clip_from_drive, clip): clip
                for clip in clips
            }

            # Collect results as they complete
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    clip = futures[future]
                    logger.error(f"Failed to process {clip.get('name', 'unknown')}: {e}")
                    results.append(ProcessingResult(
                        transaction_id="unknown",
                        worker_id=None,
                        worker_name=None,
                        confidence=0.0,
                        success=False,
                        error=str(e)
                    ))

        return results

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

            logger.info(f"Processing voice diarization for {location_name} on {date}")

            # Build worker embeddings
            if not self._build_worker_embeddings(location_name):
                logger.warning("No worker embeddings built, continuing anyway")

            # Map worker names to IDs
            self._map_worker_names_to_ids()

            # Find clips folder for date
            clips_folder = self.gdrive.get_clips_folder_for_date(location_name, date)
            if not clips_folder:
                raise ValueError(f"No clips folder found for {date}")

            # List transaction clips
            clips = self.gdrive.list_transaction_clips(clips_folder['name'])
            total_clips = len(clips)

            logger.info(f"Found {total_clips} transaction clips to process")

            # Process in batches
            for i in range(0, total_clips, self.batch_size):
                batch = clips[i:i + self.batch_size]
                batch_num = i // self.batch_size + 1
                total_batches = (total_clips + self.batch_size - 1) // self.batch_size

                logger.info(
                    f"Processing batch {batch_num}/{total_batches} "
                    f"({len(batch)} clips)"
                )

                # Process batch in parallel
                batch_results = self._process_batch_parallel(batch)

                # Update database
                for result in batch_results:
                    results['processed'] += 1

                    if result.success:
                        # Update transaction
                        update_data = {
                            'worker_id': result.worker_id,
                            'worker_assignment_source': 'voice',
                            'worker_confidence': float(result.confidence)
                        }

                        success = self.db.update_transaction_worker(
                            result.transaction_id,
                            result.worker_id,
                            result.confidence
                        )

                        # Also update with new fields
                        try:
                            self.db._request(
                                'PATCH',
                                'transactions',
                                params={'id': f'eq.{result.transaction_id}'},
                                data=update_data
                            )
                        except:
                            pass

                        if success:
                            if result.worker_id:
                                results['updated'] += 1
                                logger.info(
                                    f"✓ Updated {result.transaction_id} -> "
                                    f"{result.worker_name} ({result.confidence:.3f})"
                                )
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
                logger.info(
                    f"Progress: {results['processed']}/{total_clips} clips "
                    f"({results['updated']} matched, {results['no_match']} no match, "
                    f"{results['failures']} failures)"
                )

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            results['errors'].append(str(e))

        finally:
            # Clean up
            self._clear_gpu_memory()

        # Final summary
        logger.info("=" * 60)
        logger.info("PROCESSING COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total Processed: {results['processed']}")
        logger.info(f"Workers Matched: {results['updated']}")
        logger.info(f"No Match: {results['no_match']}")
        logger.info(f"Failures: {results['failures']}")
        logger.info("=" * 60)

        return results