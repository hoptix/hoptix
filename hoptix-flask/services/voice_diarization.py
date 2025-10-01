# import os
# import glob
# import uuid
# import wave
# import mimetypes
# import numpy as np
# import tempfile
# import logging
# from typing import Dict, Tuple, List, Optional
# from pathlib import Path

# # Audio / ML
# from pydub import AudioSegment
# import torch
# from sklearn.metrics.pairwise import cosine_similarity
# from nemo.collections.asr.models import EncDecSpeakerLabelModel

# # AssemblyAI (works with local files too)
# import assemblyai as aai

# logger = logging.getLogger(__name__)

# class VoiceDiarizationService:
#     """
#     Voice diarization service that identifies speakers in audio files
#     using AssemblyAI for transcription and NeMo TitaNet for speaker embeddings.
#     """
    
#     def __init__(self, assemblyai_api_key: str, pinecone_api_key: str = None, 
#                  samples_dir: str = None, threshold: float = 0.55, 
#                  min_utterance_ms: int = 5000):
#         """
#         Initialize the voice diarization service.
        
#         Args:
#             assemblyai_api_key: AssemblyAI API key for transcription
#             pinecone_api_key: Pinecone API key (optional, for future vector storage)
#             samples_dir: Directory containing speaker sample files
#             threshold: Minimum cosine similarity threshold for speaker matching
#             min_utterance_ms: Minimum utterance length in milliseconds for embedding extraction
#         """
#         self.assemblyai_api_key = assemblyai_api_key
#         self.pinecone_api_key = pinecone_api_key
#         self.samples_dir = samples_dir
#         self.threshold = threshold
#         self.min_utterance_ms = min_utterance_ms
        
#         # Initialize AssemblyAI
#         aai.settings.api_key = assemblyai_api_key
        
#         # Initialize speaker model (TitaNet)
#         self.speaker_model = None
#         self._load_speaker_model()
        
#         # Load speaker embeddings if samples directory is provided
#         self.speaker_embeddings = {}
#         if samples_dir:
#             self._load_speaker_embeddings()
    
#     def _load_speaker_model(self):
#         """Load the NeMo TitaNet speaker embedding model."""
#         try:
#             logger.info("Loading NeMo TitaNet speaker embedding model...")
#             self.speaker_model = EncDecSpeakerLabelModel.from_pretrained("nvidia/speakerverification_en_titanet_large")
#             logger.info("✅ Speaker model loaded successfully")
#         except Exception as e:
#             logger.error(f"Failed to load speaker model: {e}")
#             raise
    
#     def _load_speaker_embeddings(self):
#         """Load speaker embeddings from sample files in the samples directory."""
#         if not self.samples_dir or not os.path.exists(self.samples_dir):
#             logger.warning(f"Samples directory not found: {self.samples_dir}")
#             return
        
#         try:
#             sample_files = self._load_wavs_from_dir(self.samples_dir)
#             logger.info(f"Found {len(sample_files)} sample files in {self.samples_dir}")
            
#             for sample_path in sample_files:
#                 try:
#                     label = self._filename_to_label(sample_path)
#                     embedding = self._get_embedding_for_wav(sample_path)
#                     self.speaker_embeddings[label] = embedding
#                     logger.info(f"✅ Loaded embedding for speaker: {label}")
#                 except Exception as e:
#                     logger.error(f"Failed to load embedding for {sample_path}: {e}")
            
#             logger.info(f"Loaded {len(self.speaker_embeddings)} speaker embeddings")
            
#         except Exception as e:
#             logger.error(f"Failed to load speaker embeddings: {e}")
    
#     def _load_wavs_from_dir(self, directory: str) -> List[str]:
#         """Load all WAV files from a directory."""
#         return sorted(glob.glob(os.path.join(directory, "*.wav")))
    
#     def _filename_to_label(self, path: str) -> str:
#         """Convert filename to speaker label. 'Cary_Office01.wav' -> 'Cary Office01'."""
#         stem = os.path.splitext(os.path.basename(path))[0]
#         return stem.replace("_", " ").strip()
    
#     def _get_embedding_for_wav(self, wav_path: str) -> np.ndarray:
#         """Compute a (192,) embedding using TitaNet for a WAV file."""
#         emb = self.speaker_model.get_embedding(wav_path)
#         if isinstance(emb, torch.Tensor):
#             emb = emb.squeeze().cpu().numpy()
#         else:
#             emb = np.asarray(emb).squeeze()
        
#         if emb.shape != (192,):
#             raise ValueError(f"Expected (192,) embedding, got {emb.shape} for {wav_path}")
#         return emb
    
#     def _cosine_sim(self, a: np.ndarray, b: np.ndarray) -> float:
#         """Calculate cosine similarity between two embeddings."""
#         return float(cosine_similarity(a.reshape(1, -1), b.reshape(1, -1))[0][0])
    
#     def _ensure_wav_mono(self, src_path: str, out_dir: str = None) -> str:
#         """
#         Convert any local media (audio/video) to mono WAV and return the path.
#         If the input is already a mono WAV, just returns a normalized copy.
#         """
#         if out_dir is None:
#             out_dir = tempfile.mkdtemp(prefix="diarization_")
        
#         os.makedirs(out_dir, exist_ok=True)
#         base = os.path.splitext(os.path.basename(src_path))[0]
#         wav_path = os.path.join(out_dir, f"{base}.wav")

#         audio = AudioSegment.from_file(src_path)
#         if audio.channels > 1:
#             audio = audio.set_channels(1)
#         audio.export(wav_path, format="wav")
#         return wav_path
    
#     def transcribe_with_speaker_labels(self, local_media_path: str) -> dict:
#         """
#         Transcribe a LOCAL file with AssemblyAI and return json_response.
#         """
#         try:
#             config = aai.TranscriptionConfig(speaker_labels=True)
#             transcriber = aai.Transcriber(config=config)
#             transcript = transcriber.transcribe(local_media_path)
#             return transcript.json_response
#         except Exception as e:
#             logger.error(f"Failed to transcribe {local_media_path}: {e}")
#             raise
    
#     def _find_closest_speaker(self, utterance_embedding: np.ndarray) -> Tuple[str, float]:
#         """
#         Compare an utterance embedding to all known sample embeddings and
#         return (best_label, score) if above threshold; otherwise ("No match", 0).
#         """
#         if not self.speaker_embeddings:
#             return "No match", 0.0
        
#         best_label = "No match"
#         best_score = 0.0
        
#         for label, emb in self.speaker_embeddings.items():
#             score = self._cosine_sim(utterance_embedding, emb)
#             if score > best_score:
#                 best_label, best_score = label, score

#         if best_score < self.threshold:
#             return "No match", 0.0
#         return best_label, best_score
    
#     def _pick_suitable_snippet(self, utterances: List[dict], speaker_tag: str) -> dict:
#         """
#         Choose the longest utterance for a diarized speaker, preferably >= min_len_ms.
#         """
#         candidates = [u for u in utterances if u["speaker"] == speaker_tag]
#         if not candidates:
#             return None
        
#         long_enough = [u for u in candidates if (u["end"] - u["start"]) >= self.min_utterance_ms]
#         if long_enough:
#             return max(long_enough, key=lambda u: u["end"] - u["start"])
#         return max(candidates, key=lambda u: u["end"] - u["start"])
    
#     def identify_speakers_in_transcript(self, transcript_json: dict, wav_path: str) -> Tuple[List[dict], Dict[str, bool]]:
#         """
#         For each diarized speaker cluster in the transcript, compute an embedding
#         from a representative utterance, and map it to one of the known samples (if any).
#         Then relabel every utterance. Also return a presence map per sample label.
#         """
#         utterances = transcript_json.get("utterances", [])
#         if not utterances:
#             raise ValueError("No 'utterances' found in transcript. Make sure speaker_labels=True.")

#         audio = AudioSegment.from_wav(wav_path)

#         # Map diarized tags (e.g. 'A', 'B') to known labels
#         diarized_to_label: Dict[str, str] = {}

#         for diarized_speaker in sorted(set(u["speaker"] for u in utterances)):
#             chosen = self._pick_suitable_snippet(utterances, diarized_speaker)
#             if not chosen:
#                 continue
            
#             # slice audio
#             start_ms, end_ms = chosen["start"], chosen["end"]
#             seg = audio[start_ms:end_ms]
#             tmp = f"./temp_{uuid.uuid4().hex[:8]}.wav"
#             seg.export(tmp, format="wav")
            
#             try:
#                 emb = self._get_embedding_for_wav(tmp)
#                 label, score = self._find_closest_speaker(emb)
#                 logger.info(f"[Map] diarized '{diarized_speaker}' -> '{label}' (score={score:.3f})")
#                 diarized_to_label[diarized_speaker] = label
#             finally:
#                 try:
#                     os.remove(tmp)
#                 except Exception:
#                     pass

#         # Relabel every utterance's 'speaker' to the matched sample name (or 'No match')
#         relabeled = []
#         for u in utterances:
#             src = u.copy()
#             src["speaker_original"] = src["speaker"]
#             src["speaker"] = diarized_to_label.get(src["speaker_original"], "No match")
#             relabeled.append(src)

#         # Presence: a sample is present if it appears in any relabeled utterance
#         presence = {label: False for label in self.speaker_embeddings.keys()}
#         for u in relabeled:
#             if u["speaker"] in presence:
#                 presence[u["speaker"]] = True

#         return relabeled, presence
    
#     def process_audio_file(self, audio_path: str) -> dict:
#         """
#         Process an audio file for voice diarization.
        
#         Args:
#             audio_path: Path to the audio file to process
            
#         Returns:
#             Dictionary containing:
#             - transcript: Original transcript with speaker labels
#             - diarized_utterances: Utterances with identified speakers
#             - speaker_presence: Which known speakers were detected
#             - wav_path: Path to the converted WAV file
#         """
#         try:
#             logger.info(f"Processing audio file: {audio_path}")
            
#             # Convert to mono WAV if needed
#             wav_path = self._ensure_wav_mono(audio_path)
#             logger.info(f"Converted to WAV: {wav_path}")
            
#             # Transcribe with speaker labels
#             transcript = self.transcribe_with_speaker_labels(wav_path)
#             logger.info(f"Transcription completed with {len(transcript.get('utterances', []))} utterances")
            
#             # Identify speakers
#             if self.speaker_embeddings:
#                 diarized_utterances, speaker_presence = self.identify_speakers_in_transcript(transcript, wav_path)
#                 logger.info(f"Speaker identification completed. Detected speakers: {[k for k, v in speaker_presence.items() if v]}")
#             else:
#                 diarized_utterances = transcript.get("utterances", [])
#                 speaker_presence = {}
#                 logger.warning("No speaker embeddings loaded - using original speaker labels")
            
#             return {
#                 "transcript": transcript,
#                 "diarized_utterances": diarized_utterances,
#                 "speaker_presence": speaker_presence,
#                 "wav_path": wav_path
#             }
            
#         except Exception as e:
#             logger.error(f"Failed to process audio file {audio_path}: {e}")
#             raise
    
#     def add_speaker_sample(self, sample_path: str, speaker_name: str = None) -> bool:
#         """
#         Add a new speaker sample to the embeddings.
        
#         Args:
#             sample_path: Path to the speaker sample audio file
#             speaker_name: Optional custom name for the speaker
            
#         Returns:
#             True if successfully added, False otherwise
#         """
#         try:
#             if not speaker_name:
#                 speaker_name = self._filename_to_label(sample_path)
            
#             # Convert to WAV if needed
#             wav_path = self._ensure_wav_mono(sample_path)
            
#             # Get embedding
#             embedding = self._get_embedding_for_wav(wav_path)
            
#             # Store embedding
#             self.speaker_embeddings[speaker_name] = embedding
            
#             logger.info(f"✅ Added speaker sample: {speaker_name}")
#             return True
            
#         except Exception as e:
#             logger.error(f"Failed to add speaker sample {sample_path}: {e}")
#             return False
    
#     def get_speaker_list(self) -> List[str]:
#         """Get list of known speaker names."""
#         return list(self.speaker_embeddings.keys())
    
#     def clear_speaker_embeddings(self):
#         """Clear all speaker embeddings."""
#         self.speaker_embeddings.clear()
#         logger.info("Cleared all speaker embeddings")
    
#     def process_clip_for_speakers(self, clip_path: str) -> dict:
#         """
#         Process a single audio clip to identify speakers.
        
#         Args:
#             clip_path: Path to the audio clip file
            
#         Returns:
#             Dictionary containing:
#             - speakers_detected: List of detected speaker names
#             - primary_speaker: Most prominent speaker in the clip
#             - speaker_confidence: Confidence scores for each speaker
#             - utterance_count: Number of utterances in the clip
#         """
#         try:
#             logger.info(f"Processing clip for speaker identification: {clip_path}")
            
#             # Convert to mono WAV if needed
#             wav_path = self._ensure_wav_mono(clip_path)
            
#             # Transcribe with speaker labels
#             transcript = self.transcribe_with_speaker_labels(wav_path)
#             utterances = transcript.get("utterances", [])
            
#             if not utterances:
#                 logger.warning(f"No utterances found in clip: {clip_path}")
#                 return {
#                     "speakers_detected": [],
#                     "primary_speaker": "Unknown",
#                     "speaker_confidence": {},
#                     "utterance_count": 0
#                 }
            
#             # Identify speakers if we have embeddings
#             if self.speaker_embeddings:
#                 diarized_utterances, speaker_presence = self.identify_speakers_in_transcript(transcript, wav_path)
                
#                 # Count speaker occurrences
#                 speaker_counts = {}
#                 for utterance in diarized_utterances:
#                     speaker = utterance["speaker"]
#                     if speaker != "No match":
#                         speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1
                
#                 # Determine primary speaker (most utterances)
#                 primary_speaker = "Unknown"
#                 if speaker_counts:
#                     primary_speaker = max(speaker_counts, key=speaker_counts.get)
                
#                 # Calculate confidence scores (simple ratio of utterances)
#                 total_utterances = len(diarized_utterances)
#                 speaker_confidence = {
#                     speaker: count / total_utterances 
#                     for speaker, count in speaker_counts.items()
#                 }
                
#                 speakers_detected = list(speaker_counts.keys())
                
#             else:
#                 # No speaker embeddings - use original speaker labels
#                 original_speakers = set(u["speaker"] for u in utterances)
#                 speakers_detected = list(original_speakers)
#                 primary_speaker = speakers_detected[0] if speakers_detected else "Unknown"
#                 speaker_confidence = {speaker: 1.0 / len(speakers_detected) for speaker in speakers_detected}
            
#             result = {
#                 "speakers_detected": speakers_detected,
#                 "primary_speaker": primary_speaker,
#                 "speaker_confidence": speaker_confidence,
#                 "utterance_count": len(utterances)
#             }
            
#             logger.info(f"Clip analysis complete: {speakers_detected} speakers detected, primary: {primary_speaker}")
#             return result
            
#         except Exception as e:
#             logger.error(f"Failed to process clip for speakers {clip_path}: {e}")
#             return {
#                 "speakers_detected": [],
#                 "primary_speaker": "Unknown",
#                 "speaker_confidence": {},
#                 "utterance_count": 0,
#                 "error": str(e)
#             }


# # Factory function for easy initialization
# def create_voice_diarization_service(assemblyai_api_key: str, **kwargs) -> VoiceDiarizationService:
#     """
#     Factory function to create a VoiceDiarizationService instance.
    
#     Args:
#         assemblyai_api_key: AssemblyAI API key
#         **kwargs: Additional arguments for VoiceDiarizationService
        
#     Returns:
#         VoiceDiarizationService instance
#     """
#     return VoiceDiarizationService(assemblyai_api_key, **kwargs)
