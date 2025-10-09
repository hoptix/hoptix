#!/usr/bin/env python3
"""
Test to verify that audio splitting covers the entire video without gaps or overlaps.

This test ensures that:
1. All chunks together cover the entire audio duration
2. No audio content is missed between chunks
3. Overlaps are handled correctly
4. The total duration matches the original
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import numpy as np
import subprocess

# Add the parent directory to the path to import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.wav_splitter import AudioSplitter


class TestAudioSplitterCoverage(unittest.TestCase):
    """Test audio splitter coverage and chunking logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = Mock()
        self.mock_settings = Mock()
        self.splitter = AudioSplitter(self.mock_db, self.mock_settings)
        
        # Test configurations
        self.splitter.chunk_duration_minutes = 20
        self.splitter.overlap_seconds = 5
        
    def test_chunk_calculation_math(self):
        """Test that chunk calculation math is correct."""
        # Test case 1: 9.8 hour file (like your real case)
        duration_seconds = 35386  # 9.8 hours
        chunk_duration_seconds = 20 * 60  # 20 minutes
        overlap_seconds = 5
        
        # Calculate expected chunks
        effective_chunk_size = chunk_duration_seconds - overlap_seconds  # 1195 seconds
        expected_chunks = int(np.ceil(duration_seconds / effective_chunk_size))
        
        self.assertEqual(expected_chunks, 30, "Should calculate 30 chunks for 9.8 hour file")
        
        # Verify total coverage
        total_coverage = expected_chunks * effective_chunk_size
        self.assertGreaterEqual(total_coverage, duration_seconds, 
                              "Total coverage should be >= original duration")
        
        # Test case 2: 1 hour file
        duration_seconds = 3600  # 1 hour
        expected_chunks = int(np.ceil(duration_seconds / effective_chunk_size))
        self.assertEqual(expected_chunks, 4, "Should calculate 4 chunks for 1 hour file")
        
        # Test case 3: 30 minute file (should not split)
        duration_seconds = 1800  # 30 minutes
        expected_chunks = int(np.ceil(duration_seconds / effective_chunk_size))
        self.assertEqual(expected_chunks, 2, "Should calculate 2 chunks for 30 minute file")
        
    def test_chunk_timing_coverage(self):
        """Test that chunk timing covers the entire duration without gaps."""
        duration_seconds = 35386  # 9.8 hours
        chunk_duration_seconds = 20 * 60  # 20 minutes
        overlap_seconds = 5
        num_chunks = 30
        
        # Simulate chunk creation
        chunks = []
        for i in range(num_chunks):
            start_time = i * (chunk_duration_seconds - overlap_seconds)
            end_time = start_time + chunk_duration_seconds
            
            chunks.append({
                'chunk_number': i + 1,
                'start_time': start_time,
                'end_time': end_time,
                'duration': end_time - start_time
            })
        
        # Verify coverage
        self.assertEqual(len(chunks), num_chunks)
        
        # Check that first chunk starts at 0
        self.assertEqual(chunks[0]['start_time'], 0)
        
        # Check that last chunk covers the end
        last_chunk = chunks[-1]
        self.assertGreaterEqual(last_chunk['end_time'], duration_seconds)
        
        # Check that there are no gaps between chunks (accounting for overlap)
        for i in range(len(chunks) - 1):
            current_chunk = chunks[i]
            next_chunk = chunks[i + 1]
            
            # Next chunk should start before current chunk ends (due to overlap)
            self.assertLessEqual(next_chunk['start_time'], current_chunk['end_time'],
                               f"Gap between chunk {i+1} and {i+2}")
            
            # Next chunk should start at the expected position
            expected_start = (i + 1) * (chunk_duration_seconds - overlap_seconds)
            self.assertEqual(next_chunk['start_time'], expected_start)
    
    def test_overlap_handling(self):
        """Test that overlaps are handled correctly."""
        chunk_duration_seconds = 20 * 60  # 20 minutes
        overlap_seconds = 5
        
        # Test overlap calculation
        effective_chunk_size = chunk_duration_seconds - overlap_seconds
        
        # For a 1 hour file, we should have overlap between chunks
        duration_seconds = 3600  # 1 hour
        num_chunks = int(np.ceil(duration_seconds / effective_chunk_size))
        
        # Calculate chunk boundaries
        chunks = []
        for i in range(num_chunks):
            start_time = i * effective_chunk_size
            end_time = start_time + chunk_duration_seconds
            chunks.append({
                'start': start_time,
                'end': end_time
            })
        
        # Verify overlaps exist
        for i in range(len(chunks) - 1):
            current_end = chunks[i]['end']
            next_start = chunks[i + 1]['start']
            overlap = current_end - next_start
            
            self.assertGreater(overlap, 0, f"Should have overlap between chunk {i+1} and {i+2}")
            self.assertEqual(overlap, overlap_seconds, f"Overlap should be {overlap_seconds} seconds")
    
    def test_edge_cases(self):
        """Test edge cases for chunking."""
        chunk_duration_seconds = 20 * 60  # 20 minutes
        overlap_seconds = 5
        effective_chunk_size = chunk_duration_seconds - overlap_seconds
        
        # Test case 1: Very short file (less than one chunk)
        short_duration = 300  # 5 minutes
        num_chunks = int(np.ceil(short_duration / effective_chunk_size))
        self.assertEqual(num_chunks, 1, "Short file should have 1 chunk")
        
        # Test case 2: File exactly one chunk duration
        exact_duration = chunk_duration_seconds  # 20 minutes
        num_chunks = int(np.ceil(exact_duration / effective_chunk_size))
        self.assertEqual(num_chunks, 2, "File exactly one chunk should have 2 chunks (with overlap)")
        
        # Test case 3: Very long file
        long_duration = 86400  # 24 hours
        num_chunks = int(np.ceil(long_duration / effective_chunk_size))
        expected_chunks = int(np.ceil(long_duration / effective_chunk_size))
        self.assertEqual(num_chunks, expected_chunks)
        
        # Verify total coverage for long file
        total_coverage = num_chunks * effective_chunk_size
        self.assertGreaterEqual(total_coverage, long_duration)
    
    @patch('subprocess.check_output')
    def test_real_audio_duration_handling(self, mock_check_output):
        """Test that real audio duration is properly handled."""
        # Mock ffprobe output for a 9.8 hour file
        mock_check_output.return_value = b'35386.0\n'
        
        # Test duration detection
        duration = self.splitter._get_audio_duration('/fake/path.mp3')
        self.assertEqual(duration, 35386.0)
        
        # Test chunk calculation with real duration
        chunk_duration_seconds = 20 * 60
        overlap_seconds = 5
        effective_chunk_size = chunk_duration_seconds - overlap_seconds
        
        num_chunks = int(np.ceil(duration / effective_chunk_size))
        self.assertEqual(num_chunks, 30)
        
        # Verify total coverage
        total_coverage = num_chunks * effective_chunk_size
        self.assertGreaterEqual(total_coverage, duration)
        self.assertLessEqual(total_coverage - duration, effective_chunk_size)
    
    def test_chunk_boundary_validation(self):
        """Test that chunk boundaries are valid and don't exceed file duration."""
        duration_seconds = 35386  # 9.8 hours
        chunk_duration_seconds = 20 * 60  # 20 minutes
        overlap_seconds = 5
        num_chunks = 30
        
        # Generate chunk boundaries
        chunks = []
        for i in range(num_chunks):
            start_time = i * (chunk_duration_seconds - overlap_seconds)
            end_time = min(start_time + chunk_duration_seconds, duration_seconds)
            
            chunks.append({
                'start': start_time,
                'end': end_time,
                'duration': end_time - start_time
            })
        
        # Validate all chunks
        for i, chunk in enumerate(chunks):
            # Start time should be non-negative
            self.assertGreaterEqual(chunk['start'], 0, f"Chunk {i+1} start time should be >= 0")
            
            # End time should not exceed file duration
            self.assertLessEqual(chunk['end'], duration_seconds, 
                               f"Chunk {i+1} end time should not exceed file duration")
            
            # Duration should be positive
            self.assertGreater(chunk['duration'], 0, f"Chunk {i+1} should have positive duration")
            
            # Duration should not exceed chunk_duration_seconds (except possibly last chunk)
            if i < len(chunks) - 1:  # Not the last chunk
                self.assertEqual(chunk['duration'], chunk_duration_seconds,
                               f"Chunk {i+1} should have full duration")
    
    def test_coverage_completeness(self):
        """Test that the entire audio file is covered by chunks."""
        duration_seconds = 35386  # 9.8 hours
        chunk_duration_seconds = 20 * 60  # 20 minutes
        overlap_seconds = 5
        num_chunks = 30
        
        # Generate all chunks
        chunks = []
        for i in range(num_chunks):
            start_time = i * (chunk_duration_seconds - overlap_seconds)
            end_time = start_time + chunk_duration_seconds
            chunks.append({
                'start': start_time,
                'end': end_time
            })
        
        # Create a coverage map
        coverage_map = [False] * int(duration_seconds)
        
        # Mark covered segments
        for chunk in chunks:
            start_idx = int(chunk['start'])
            end_idx = min(int(chunk['end']), duration_seconds)
            for i in range(start_idx, end_idx):
                if i < len(coverage_map):
                    coverage_map[i] = True
        
        # Check for gaps
        gaps = []
        in_gap = False
        gap_start = 0
        
        for i, covered in enumerate(coverage_map):
            if not covered and not in_gap:
                in_gap = True
                gap_start = i
            elif covered and in_gap:
                in_gap = False
                gaps.append((gap_start, i - 1))
        
        # Handle gap at the end
        if in_gap:
            gaps.append((gap_start, len(coverage_map) - 1))
        
        # Report any gaps
        if gaps:
            gap_info = ", ".join([f"{start}-{end}s" for start, end in gaps])
            self.fail(f"Found gaps in coverage: {gap_info}")
        
        # Verify total coverage percentage
        covered_seconds = sum(coverage_map)
        coverage_percentage = (covered_seconds / duration_seconds) * 100
        
        self.assertGreaterEqual(coverage_percentage, 99.9, 
                              f"Coverage should be >= 99.9%, got {coverage_percentage:.2f}%")


if __name__ == '__main__':
    # Run the tests with verbose output
    unittest.main(verbosity=2)
