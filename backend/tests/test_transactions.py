#!/usr/bin/env python3
"""
Test suite for transaction splitting functionality
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch
from services.transactions import split_into_transactions


class TestTransactionSplitting:
    """Test cases for split_into_transactions function"""
    
    def setup_method(self):
        """Set up test data"""
        self.test_date = "2025-10-15"
        self.audio_start_time = "10:00:00Z"
        
        # Sample transcript segments with realistic operator-customer conversations
        self.sample_transcript_segments = [
            {
                "text": """Operator: Hi, welcome to Dairy Queen! How can I help you today?
Customer: Hi! I'd like to order a large Blizzard, please.
Operator: Great! What flavor would you like?
Customer: I'll have the Oreo Blizzard.
Operator: Perfect! Would you like to make that a meal with fries and a drink?
Customer: Yes, that sounds good. I'll have medium fries and a large Coke.
Operator: Excellent! Your total is $8.50. Will that be all?
Customer: Yes, that's everything. Thank you!
Operator: Thank you! Your order will be ready in about 5 minutes.""",
                "start": 0.0,
                "end": 45.2
            },
            {
                "text": """Operator: Hi there! What can I get for you?
Customer: I need two Whopper meals, please.
Operator: Sure! Would you like to upsize those to large meals?
Customer: Yes, please. And can I add extra cheese to both?
Operator: Absolutely! Your total comes to $18.75.
Customer: Perfect. I'll pay with card.
Operator: Great! Your order number is 47. It'll be ready in 8-10 minutes.""",
                "start": 45.2,
                "end": 78.5
            },
            {
                "text": """Customer: Excuse me, I'd like to order a small sundae.
Operator: Of course! What toppings would you like?
Customer: Just whipped cream, please.
Operator: Would you like to add any other toppings like nuts or sprinkles?
Customer: No, just whipped cream is fine.
Operator: Perfect! That'll be $3.25.
Customer: Thank you!""",
                "start": 78.5,
                "end": 95.0
            }
        ]
    
    @patch('services.transactions.client.responses.create')
    def test_successful_transaction_splitting(self, mock_openai):
        """Test that transactions are split correctly with proper timing"""
        
        # Mock OpenAI responses for each transcript segment
        mock_responses = [
            # First transaction - complete order
            Mock(output=[
                Mock(content=[Mock(text="")]),  # First output (empty)
                Mock(content=[Mock(text='{"1": "Hi, welcome to Dairy Queen! How can I help you today? Hi! I\'d like to order a large Blizzard, please. Great! What flavor would you like? I\'ll have the Oreo Blizzard. Perfect! Would you like to make that a meal with fries and a drink? Yes, that sounds good. I\'ll have medium fries and a large Coke. Excellent! Your total is $8.50. Will that be all? Yes, that\'s everything. Thank you! Thank you! Your order will be ready in about 5 minutes.", "2": "1", "3": "0", "4": "0", "5": "0", "6": "0"}')])
            ]),
            # Second transaction - complete order with upsell
            Mock(output=[
                Mock(content=[Mock(text="")]),
                Mock(content=[Mock(text='{"1": "Hi there! What can I get for you? I need two Whopper meals, please. Sure! Would you like to upsize those to large meals? Yes, please. And can I add extra cheese to both? Absolutely! Your total comes to $18.75. Perfect. I\'ll pay with card. Great! Your order number is 47. It\'ll be ready in 8-10 minutes.", "2": "1", "3": "0", "4": "0", "5": "0", "6": "0"}')])
            ]),
            # Third transaction - simple order
            Mock(output=[
                Mock(content=[Mock(text="")]),
                Mock(content=[Mock(text='{"1": "Excuse me, I\'d like to order a small sundae. Of course! What toppings would you like? Just whipped cream, please. Would you like to add any other toppings like nuts or sprinkles? No, just whipped cream is fine. Perfect! That\'ll be $3.25. Thank you!", "2": "1", "3": "0", "4": "0", "5": "0", "6": "0"}')])
            ])
        ]
        
        mock_openai.side_effect = mock_responses
        
        # Execute the function
        results = split_into_transactions(
            self.sample_transcript_segments, 
            self.test_date, 
            self.audio_start_time
        )
        
        # Verify results
        assert len(results) == 3, f"Expected 3 transactions, got {len(results)}"
        
        # Check first transaction
        first_tx = results[0]
        assert first_tx["kind"] == "order"
        assert first_tx["meta"]["complete_order"] == 1
        assert first_tx["meta"]["mobile_order"] == 0
        assert first_tx["meta"]["coupon_used"] == 0
        assert first_tx["meta"]["asked_more_time"] == 0
        assert first_tx["meta"]["out_of_stock_items"] == "0"
        assert "Blizzard" in first_tx["meta"]["text"]
        assert first_tx["meta"]["segment_index"] == 0
        assert first_tx["meta"]["total_segments_in_audio"] == 1
        
        # Check timing for first transaction
        from datetime import datetime
        expected_start = datetime.fromisoformat("2025-10-15T10:00:00+00:00")
        expected_end = datetime.fromisoformat("2025-10-15T10:00:45.2+00:00")
        actual_start = datetime.fromisoformat(first_tx["started_at"])
        actual_end = datetime.fromisoformat(first_tx["ended_at"])
        assert actual_start == expected_start
        assert actual_end == expected_end
        
        # Check second transaction
        second_tx = results[1]
        assert second_tx["meta"]["complete_order"] == 1
        assert "Whopper" in second_tx["meta"]["text"]
        assert second_tx["meta"]["segment_index"] == 0
        assert second_tx["meta"]["total_segments_in_audio"] == 1
        
        # Check third transaction
        third_tx = results[2]
        assert third_tx["meta"]["complete_order"] == 1
        assert "sundae" in third_tx["meta"]["text"]
        assert third_tx["meta"]["segment_index"] == 0
        assert third_tx["meta"]["total_segments_in_audio"] == 1
    
    @patch('services.transactions.client.responses.create')
    def test_multiple_transactions_in_single_segment(self, mock_openai):
        """Test splitting when one transcript segment contains multiple transactions"""
        
        # Mock response that indicates multiple transactions
        mock_response = Mock(output=[
            Mock(content=[Mock(text="")]),
            Mock(content=[Mock(text='{"1": "First transaction text", "2": "1", "3": "0", "4": "0", "5": "0", "6": "0"}@#&{"1": "Second transaction text", "2": "1", "3": "0", "4": "0", "5": "0", "6": "0"}')])
        ])
        mock_openai.return_value = mock_response
        
        # Single segment that should be split into two transactions
        segments = [{
            "text": "First transaction. Second transaction.",
            "start": 0.0,
            "end": 30.0
        }]
        
        results = split_into_transactions(segments, self.test_date, self.audio_start_time)
        
        # Should create 2 transactions from 1 segment
        assert len(results) == 2
        
        # Check timing is split correctly
        first_tx = results[0]
        second_tx = results[1]
        
        # First transaction should be 0-15 seconds
        expected_first_start = "2025-10-15T10:00:00+00:00"
        expected_first_end = "2025-10-15T10:00:15+00:00"
        assert first_tx["started_at"] == expected_first_start
        assert first_tx["ended_at"] == expected_first_end
        
        # Second transaction should be 15-30 seconds
        expected_second_start = "2025-10-15T10:00:15+00:00"
        expected_second_end = "2025-10-15T10:00:30+00:00"
        assert second_tx["started_at"] == expected_second_start
        assert second_tx["ended_at"] == expected_second_end
        
        # Check metadata
        assert first_tx["meta"]["segment_index"] == 0
        assert first_tx["meta"]["total_segments_in_audio"] == 2
        assert second_tx["meta"]["segment_index"] == 1
        assert second_tx["meta"]["total_segments_in_audio"] == 2
    
    @patch('services.transactions.client.responses.create')
    def test_incomplete_order_handling(self, mock_openai):
        """Test handling of incomplete orders"""
        
        mock_response = Mock(output=[
            Mock(content=[Mock(text="")]),
            Mock(content=[Mock(text='{"1": "Customer called but didn\'t complete order", "2": "0", "3": "0", "4": "0", "5": "1", "6": "0"}')])
        ])
        mock_openai.return_value = mock_response
        
        segments = [{
            "text": "Customer called but didn't complete order",
            "start": 0.0,
            "end": 20.0
        }]
        
        results = split_into_transactions(segments, self.test_date, self.audio_start_time)
        
        assert len(results) == 1
        tx = results[0]
        assert tx["meta"]["complete_order"] == 0
        assert tx["meta"]["asked_more_time"] == 1
    
    @patch('services.transactions.client.responses.create')
    def test_mobile_order_handling(self, mock_openai):
        """Test handling of mobile orders"""
        
        mock_response = Mock(output=[
            Mock(content=[Mock(text="")]),
            Mock(content=[Mock(text='{"1": "Mobile order pickup", "2": "1", "3": "1", "4": "0", "5": "0", "6": "0"}')])
        ])
        mock_openai.return_value = mock_response
        
        segments = [{
            "text": "Mobile order pickup",
            "start": 0.0,
            "end": 15.0
        }]
        
        results = split_into_transactions(segments, self.test_date, self.audio_start_time)
        
        assert len(results) == 1
        tx = results[0]
        assert tx["meta"]["complete_order"] == 1
        assert tx["meta"]["mobile_order"] == 1
    
    @patch('services.transactions.client.responses.create')
    def test_coupon_usage_handling(self, mock_openai):
        """Test handling of coupon usage"""
        
        mock_response = Mock(output=[
            Mock(content=[Mock(text="")]),
            Mock(content=[Mock(text='{"1": "Order with coupon", "2": "1", "3": "0", "4": "1", "5": "0", "6": "0"}')])
        ])
        mock_openai.return_value = mock_response
        
        segments = [{
            "text": "Order with coupon",
            "start": 0.0,
            "end": 25.0
        }]
        
        results = split_into_transactions(segments, self.test_date, self.audio_start_time)
        
        assert len(results) == 1
        tx = results[0]
        assert tx["meta"]["complete_order"] == 1
        assert tx["meta"]["coupon_used"] == 1
    
    @patch('services.transactions.client.responses.create')
    def test_out_of_stock_items_handling(self, mock_openai):
        """Test handling of out of stock items"""
        
        mock_response = Mock(output=[
            Mock(content=[Mock(text="")]),
            Mock(content=[Mock(text='{"1": "Order with out of stock items", "2": "1", "3": "0", "4": "0", "5": "0", "6": "Chicken Sandwich, Large Fries"}')])
        ])
        mock_openai.return_value = mock_response
        
        segments = [{
            "text": "Order with out of stock items",
            "start": 0.0,
            "end": 30.0
        }]
        
        results = split_into_transactions(segments, self.test_date, self.audio_start_time)
        
        assert len(results) == 1
        tx = results[0]
        assert tx["meta"]["complete_order"] == 1
        assert tx["meta"]["out_of_stock_items"] == "Chicken Sandwich, Large Fries"
    
    @patch('services.transactions.client.responses.create')
    def test_empty_transcript_handling(self, mock_openai):
        """Test handling of empty or whitespace-only transcripts"""
        
        segments = [
            {"text": "", "start": 0.0, "end": 5.0},
            {"text": "   ", "start": 5.0, "end": 10.0},
            {"text": "Valid transaction", "start": 10.0, "end": 20.0}
        ]
        
        # Only the valid segment should trigger an API call
        mock_response = Mock(output=[
            Mock(content=[Mock(text="")]),
            Mock(content=[Mock(text='{"1": "Valid transaction", "2": "1", "3": "0", "4": "0", "5": "0", "6": "0"}')])
        ])
        mock_openai.return_value = mock_response
        
        results = split_into_transactions(segments, self.test_date, self.audio_start_time)
        
        # Should only process the valid segment
        assert len(results) == 1
        assert results[0]["meta"]["text"] == "Valid transaction"
        assert mock_openai.call_count == 1  # Only called once for valid segment
    
    @patch('services.transactions.client.responses.create')
    def test_malformed_json_handling(self, mock_openai):
        """Test handling of malformed JSON responses"""
        
        mock_response = Mock(output=[
            Mock(content=[Mock(text="")]),
            Mock(content=[Mock(text="Invalid JSON response")])
        ])
        mock_openai.return_value = mock_response
        
        segments = [{
            "text": "Test transaction",
            "start": 0.0,
            "end": 15.0
        }]
        
        results = split_into_transactions(segments, self.test_date, self.audio_start_time)
        
        # Should still create a transaction with fallback values
        assert len(results) == 1
        tx = results[0]
        assert tx["meta"]["text"] == "Test transaction"  # Original text
        assert tx["meta"]["complete_order"] == 0  # Default fallback
        assert tx["meta"]["mobile_order"] == 0
        assert tx["meta"]["coupon_used"] == 0
        assert tx["meta"]["asked_more_time"] == 0
        assert tx["meta"]["out_of_stock_items"] == "0"
    
    @patch('services.transactions.client.responses.create')
    def test_timing_accuracy(self, mock_openai):
        """Test that timing calculations are accurate"""
        
        mock_response = Mock(output=[
            Mock(content=[Mock(text="")]),
            Mock(content=[Mock(text='{"1": "Test transaction", "2": "1", "3": "0", "4": "0", "5": "0", "6": "0"}')])
        ])
        mock_openai.return_value = mock_response
        
        # Test with precise timing
        segments = [{
            "text": "Test transaction",
            "start": 10.5,
            "end": 25.7
        }]
        
        results = split_into_transactions(segments, self.test_date, self.audio_start_time)
        
        assert len(results) == 1
        tx = results[0]
        
        # Check that timing is calculated correctly
        from datetime import datetime
        expected_start = datetime.fromisoformat("2025-10-15T10:00:10.5+00:00")
        expected_end = datetime.fromisoformat("2025-10-15T10:00:25.7+00:00")
        actual_start = datetime.fromisoformat(tx["started_at"])
        actual_end = datetime.fromisoformat(tx["ended_at"])
        assert actual_start == expected_start
        assert actual_end == expected_end
        assert tx["meta"]["audio_start_seconds"] == 10.5
        assert tx["meta"]["audio_end_seconds"] == 25.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
