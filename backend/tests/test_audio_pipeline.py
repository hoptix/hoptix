import sys
import os
import tempfile
import numpy as np
import soundfile as sf
from unittest.mock import Mock, patch, MagicMock
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.audio import AudioTransactionProcessor
from services.transcribe import transcribe_audio_clip
from pipeline.full_pipeline import full_pipeline


class TestAudioTransactionProcessor:
    """Test the AudioTransactionProcessor class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.processor = AudioTransactionProcessor()
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_audio_file(self, duration_seconds=60, sample_rate=44100, 
                              silence_periods=None, filename="test_audio.wav"):
        """Create a test audio file with configurable silence periods"""
        if silence_periods is None:
            silence_periods = [(20, 25), (40, 45)]  # Default silence periods
        
        # Create audio data
        total_samples = int(duration_seconds * sample_rate)
        audio_data = np.random.normal(0, 0.1, total_samples)  # Background noise
        
        # Add silence periods
        for start_sec, end_sec in silence_periods:
            start_sample = int(start_sec * sample_rate)
            end_sample = int(end_sec * sample_rate)
            audio_data[start_sample:end_sample] = 0.0
        
        # Save to file
        file_path = os.path.join(self.temp_dir, filename)
        sf.write(file_path, audio_data, sample_rate)
        return file_path
    
    def test_create_audio_subclips_basic(self):
        """Test basic audio subclip creation"""
        # Create test audio with 2 silence periods (should create 3 transactions)
        audio_path = self.create_test_audio_file(
            duration_seconds=60,
            silence_periods=[(20, 25), (40, 45)]
        )
        
        # Process audio
        clip_paths, begin_times, end_times, reg_begin_times, reg_end_times = self.processor.create_audio_subclips(
            audio_path, "test_location", self.temp_dir
        )
        
        # Verify results
        assert len(clip_paths) > 0, "Should create at least one clip"
        assert len(begin_times) == len(end_times), "Begin and end times should match"
        assert len(clip_paths) == len(begin_times), "Clip paths should match timing data"
        
        # Verify clips were created
        successful_clips = [p for p in clip_paths if p and os.path.exists(p)]
        assert len(successful_clips) > 0, "Should have at least one successful clip"
        
        # Verify clip durations are reasonable
        for i, (begin, end) in enumerate(zip(begin_times, end_times)):
            duration = end - begin
            assert duration > 0, f"Clip {i} should have positive duration"
            assert duration <= 60, f"Clip {i} should not be longer than total audio"
    
    def test_create_audio_subclips_no_silence(self):
        """Test audio with no silence periods (should create one clip)"""
        # Create test audio with no silence
        audio_path = self.create_test_audio_file(
            duration_seconds=30,
            silence_periods=[]
        )
        
        clip_paths, begin_times, end_times, reg_begin_times, reg_end_times = self.processor.create_audio_subclips(
            audio_path, "test_location", self.temp_dir
        )
        
        # Should create one clip for the entire audio
        assert len(clip_paths) == 1, "Should create one clip for audio with no silence"
        assert begin_times[0] == 0.0, "First clip should start at 0"
        assert end_times[0] > 25, "First clip should end near the audio duration"
    
    def test_create_audio_subclips_invalid_file(self):
        """Test handling of invalid audio file"""
        invalid_path = os.path.join(self.temp_dir, "nonexistent.wav")
        
        clip_paths, begin_times, end_times, reg_begin_times, reg_end_times = self.processor.create_audio_subclips(
            invalid_path, "test_location", self.temp_dir
        )
        
        # Should return empty results
        assert len(clip_paths) == 0, "Should return empty results for invalid file"
        assert len(begin_times) == 0, "Should return empty begin times"
        assert len(end_times) == 0, "Should return empty end times"
    
    def test_timestamp_conversion(self):
        """Test timestamp conversion functionality"""
        # Test with a mock filename
        test_seconds = 3661  # 1 hour, 1 minute, 1 second
        mock_audio_path = "location_20240115120000.wav"
        
        result = self.processor._convert_timestamp_to_hhmmss(test_seconds, mock_audio_path)
        
        # Should return HH:MM:SS format
        assert ":" in result, "Should contain colons for time format"
        parts = result.split(":")
        assert len(parts) == 3, "Should have 3 parts (hours:minutes:seconds)"
        assert all(part.isdigit() for part in parts), "All parts should be digits"
    
    def test_filename_generation(self):
        """Test filename generation for clips"""
        mock_audio_path = "location_20240115120000.wav"
        begin_timestamp = "12:30:45"
        index = 0
        
        filename = self.processor._generate_clip_filename("test_location", mock_audio_path, begin_timestamp, index)
        
        # Should contain location and timestamp info
        assert "test_location" in filename, "Should contain location ID"
        assert "2024" in filename, "Should contain year"
        assert "01" in filename, "Should contain month"
        assert "15" in filename, "Should contain day"
        assert filename.endswith(".mp3"), "Should end with .mp3 extension"


class TestTranscribeAudioClip:
    """Test the transcribe_audio_clip function"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_audio_file(self, duration_seconds=10, sample_rate=44100):
        """Create a simple test audio file"""
        total_samples = int(duration_seconds * sample_rate)
        audio_data = np.random.normal(0, 0.1, total_samples)
        
        file_path = os.path.join(self.temp_dir, "test_clip.wav")
        sf.write(file_path, audio_data, sample_rate)
        return file_path
    
    @patch('services.transcribe.client')
    def test_transcribe_audio_clip_success(self, mock_client):
        """Test successful audio clip transcription"""
        # Create test audio file
        audio_path = self.create_test_audio_file(duration_seconds=5)
        
        # Mock OpenAI response
        mock_client.audio.transcriptions.create.return_value = "Operator: Hello, welcome to Dairy Queen. Customer: Hi, I'd like a number 1 meal."
        
        # Test transcription
        result = transcribe_audio_clip(audio_path, 0.0, 5.0, 0)
        
        # Verify results
        assert 'error' not in result, "Should not have error in successful transcription"
        assert result['transcript'] == "Operator: Hello, welcome to Dairy Queen. Customer: Hi, I'd like a number 1 meal."
        assert result['begin_time'] == 0.0
        assert result['end_time'] == 5.0
        assert result['index'] == 0
        assert result['audio_price'] > 0, "Should have positive audio price"
        assert 'audio_duration' in result, "Should include audio duration"
        assert 'clip_path' in result, "Should include clip path"
        
        # Verify OpenAI was called
        mock_client.audio.transcriptions.create.assert_called_once()
    
    def test_transcribe_audio_clip_file_not_found(self):
        """Test transcription with non-existent file"""
        invalid_path = os.path.join(self.temp_dir, "nonexistent.wav")
        
        result = transcribe_audio_clip(invalid_path, 0.0, 5.0, 0)
        
        # Should return error
        assert 'error' in result, "Should have error for non-existent file"
        assert result['transcript'] == "", "Should have empty transcript"
        assert result['audio_price'] == 0.0, "Should have zero price"
    
    @patch('services.transcribe.client')
    def test_transcribe_audio_clip_api_error(self, mock_client):
        """Test transcription with API error"""
        # Create test audio file
        audio_path = self.create_test_audio_file(duration_seconds=5)
        
        # Mock API error
        mock_client.audio.transcriptions.create.side_effect = Exception("API Error")
        
        result = transcribe_audio_clip(audio_path, 0.0, 5.0, 0)
        
        # Should return error
        assert 'error' in result, "Should have error for API failure"
        assert "API Error" in result['error'], "Should include the error message"
        assert result['transcript'] == "", "Should have empty transcript"


class TestFullPipelineIntegration:
    """Test the full pipeline integration"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('pipeline.full_pipeline.get_audio_from_location_and_date')
    @patch('pipeline.full_pipeline.db')
    @patch('pipeline.full_pipeline.transcribe_audio_clip')
    @patch('pipeline.full_pipeline.grade_transactions')
    @patch('pipeline.full_pipeline.Analytics')
    @patch('pipeline.full_pipeline.clip_transactions')
    def test_full_pipeline_integration(self, mock_clip_transactions, mock_analytics, 
                                     mock_grade_transactions, mock_transcribe_audio_clip,
                                     mock_db, mock_get_audio):
        """Test the full pipeline integration with mocked dependencies"""
        
        # Create test audio file
        audio_path = os.path.join(self.temp_dir, "test_audio.wav")
        total_samples = int(30 * 44100)  # 30 seconds
        audio_data = np.random.normal(0, 0.1, total_samples)
        sf.write(audio_path, audio_data, 44100)
        
        # Mock dependencies
        mock_get_audio.return_value = (audio_path, "gdrive_path")
        mock_db.get_location_name.return_value = "Test Location"
        mock_db.insert_run.return_value = "test_run_id"
        mock_db.audio_exists.return_value = False
        mock_db.create_audio.return_value = "test_audio_id"
        mock_db.upsert_transactions.return_value = [{"id": "test_transaction_id"}]
        mock_db.upsert_grades.return_value = None
        mock_db.set_pipeline_to_complete.return_value = None
        
        # Mock transcription results
        mock_transcribe_audio_clip.return_value = {
            'transcript': 'Operator: Hello, welcome to Dairy Queen. Customer: Hi, I\'d like a number 1 meal.',
            'audio_price': 0.001,
            'begin_time': 0.0,
            'end_time': 10.0,
            'audio_duration': 10.0,
            'clip_path': audio_path
        }
        
        # Mock grading results
        mock_grade_transactions.return_value = [{"transaction_id": "test_transaction_id", "grade": "A"}]
        
        # Mock analytics
        mock_analytics_instance = Mock()
        mock_analytics.return_value = mock_analytics_instance
        
        # Run pipeline
        result = full_pipeline("test_location_id", "2024-01-15")
        
        # Verify result
        assert result == "Successfully completed full pipeline", "Pipeline should complete successfully"
        
        # Verify key calls were made
        mock_get_audio.assert_called_once_with("test_location_id", "2024-01-15")
        mock_db.insert_run.assert_called_once_with("test_location_id", "2024-01-15")
        mock_db.create_audio.assert_called_once()
        mock_db.upsert_transactions.assert_called_once()
        mock_grade_transactions.assert_called_once()
        mock_db.upsert_grades.assert_called_once()
        mock_analytics.assert_called_once_with("test_run_id")
        mock_analytics_instance.upload_to_db.assert_called_once()
        mock_clip_transactions.assert_called_once()
        mock_db.set_pipeline_to_complete.assert_called_once_with("test_run_id", "test_audio_id")


def run_audio_pipeline_tests():
    """Run all audio pipeline tests"""
    print("🧪 Running Audio Pipeline Tests...")
    
    # Test AudioTransactionProcessor
    print("\n📊 Testing AudioTransactionProcessor...")
    processor_tests = TestAudioTransactionProcessor()
    processor_tests.setup_method()
    
    try:
        processor_tests.test_create_audio_subclips_basic()
        print("✅ Basic audio subclip creation test passed")
        
        processor_tests.test_create_audio_subclips_no_silence()
        print("✅ No silence audio subclip test passed")
        
        processor_tests.test_create_audio_subclips_invalid_file()
        print("✅ Invalid file handling test passed")
        
        processor_tests.test_timestamp_conversion()
        print("✅ Timestamp conversion test passed")
        
        processor_tests.test_filename_generation()
        print("✅ Filename generation test passed")
        
    except Exception as e:
        print(f"❌ AudioTransactionProcessor test failed: {e}")
    finally:
        processor_tests.teardown_method()
    
    # Test transcribe_audio_clip
    print("\n🎵 Testing transcribe_audio_clip...")
    transcribe_tests = TestTranscribeAudioClip()
    transcribe_tests.setup_method()
    
    try:
        transcribe_tests.test_transcribe_audio_clip_success()
        print("✅ Successful transcription test passed")
        
        transcribe_tests.test_transcribe_audio_clip_file_not_found()
        print("✅ File not found handling test passed")
        
        transcribe_tests.test_transcribe_audio_clip_api_error()
        print("✅ API error handling test passed")
        
    except Exception as e:
        print(f"❌ transcribe_audio_clip test failed: {e}")
    finally:
        transcribe_tests.teardown_method()
    
    # Test full pipeline integration
    print("\n🚀 Testing full pipeline integration...")
    pipeline_tests = TestFullPipelineIntegration()
    pipeline_tests.setup_method()
    
    try:
        pipeline_tests.test_full_pipeline_integration()
        print("✅ Full pipeline integration test passed")
        
    except Exception as e:
        print(f"❌ Full pipeline integration test failed: {e}")
    finally:
        pipeline_tests.teardown_method()
    
    print("\n🎉 All audio pipeline tests completed!")


if __name__ == "__main__":
    run_audio_pipeline_tests()
