import json
import boto3
import logging
from typing import Dict, Optional, List
from datetime import datetime
from dataclasses import asdict

logger = logging.getLogger(__name__)

class SQSClient:
    """SQS client for video processing queue"""
    
    def __init__(self, region: str, queue_url: str, dlq_url: str = None):
        self.region = region
        self.queue_url = queue_url
        self.dlq_url = dlq_url
        self.sqs = boto3.client('sqs', region_name=region)
        logger.info(f"Initialized SQS client for queue: {queue_url}")
    
    def send_video_message(self, video_data: Dict, delay_seconds: int = 0) -> str:
        """
        Send a video processing message to SQS
        
        Args:
            video_data: Dictionary containing video info (id, s3_key, run_id, etc.)
            delay_seconds: Delay before message becomes visible (0-900 seconds)
        
        Returns:
            Message ID
        """
        message_body = {
            "video_id": video_data["id"],
            "s3_key": video_data["s3_key"],
            "run_id": video_data["run_id"],
            "location_id": video_data["location_id"],
            "started_at": video_data["started_at"],
            "ended_at": video_data["ended_at"],
            "enqueued_at": datetime.now().isoformat(),
            "retry_count": 0
        }
        
        try:
            response = self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message_body),
                DelaySeconds=delay_seconds,
                MessageAttributes={
                    'video_id': {
                        'StringValue': video_data["id"],
                        'DataType': 'String'
                    },
                    'run_id': {
                        'StringValue': video_data["run_id"],
                        'DataType': 'String'
                    },
                    'location_id': {
                        'StringValue': video_data["location_id"],
                        'DataType': 'String'
                    }
                }
            )
            
            message_id = response['MessageId']
            logger.info(f"Sent video {video_data['id']} to SQS queue: {message_id}")
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to send message for video {video_data['id']}: {e}")
            raise
    
    def receive_video_message(self, wait_time_seconds: int = 20, visibility_timeout: int = 1800) -> Optional[Dict]:
        """
        Receive a video processing message from SQS
        
        Args:
            wait_time_seconds: Long polling wait time (0-20 seconds)
            visibility_timeout: How long message is hidden from other consumers (seconds)
        
        Returns:
            Dict with message data and receipt_handle, or None if no messages
        """
        try:
            response = self.sqs.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=wait_time_seconds,
                VisibilityTimeout=visibility_timeout,
                MessageAttributeNames=['All']
            )
            
            messages = response.get('Messages', [])
            if not messages:
                return None
            
            message = messages[0]
            message_body = json.loads(message['Body'])
            
            return {
                'receipt_handle': message['ReceiptHandle'],
                'video_data': message_body,
                'message_id': message['MessageId'],
                'attributes': message.get('MessageAttributes', {})
            }
            
        except Exception as e:
            logger.error(f"Failed to receive message from SQS: {e}")
            return None
    
    def delete_message(self, receipt_handle: str) -> bool:
        """
        Delete a processed message from SQS
        
        Args:
            receipt_handle: Receipt handle from receive_message
        
        Returns:
            True if successful
        """
        try:
            self.sqs.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle
            )
            logger.debug("Successfully deleted message from queue")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")
            return False
    
    def change_message_visibility(self, receipt_handle: str, visibility_timeout: int) -> bool:
        """
        Change the visibility timeout of a message (extend processing time)
        
        Args:
            receipt_handle: Receipt handle from receive_message
            visibility_timeout: New visibility timeout in seconds
        
        Returns:
            True if successful
        """
        try:
            self.sqs.change_message_visibility(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=visibility_timeout
            )
            logger.debug(f"Extended message visibility to {visibility_timeout} seconds")
            return True
            
        except Exception as e:
            logger.error(f"Failed to change message visibility: {e}")
            return False
    
    def get_queue_attributes(self) -> Dict:
        """
        Get queue statistics and attributes
        
        Returns:
            Dictionary with queue metrics
        """
        try:
            response = self.sqs.get_queue_attributes(
                QueueUrl=self.queue_url,
                AttributeNames=[
                    'ApproximateNumberOfMessages',
                    'ApproximateNumberOfMessagesNotVisible',
                    'ApproximateNumberOfMessagesDelayed'
                ]
            )
            
            attributes = response.get('Attributes', {})
            return {
                'messages_available': int(attributes.get('ApproximateNumberOfMessages', 0)),
                'messages_in_flight': int(attributes.get('ApproximateNumberOfMessagesNotVisible', 0)),
                'messages_delayed': int(attributes.get('ApproximateNumberOfMessagesDelayed', 0))
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue attributes: {e}")
            return {}
    
    def get_dlq_attributes(self) -> Dict:
        """
        Get dead letter queue statistics (if configured)
        
        Returns:
            Dictionary with DLQ metrics
        """
        if not self.dlq_url:
            return {}
        
        try:
            response = self.sqs.get_queue_attributes(
                QueueUrl=self.dlq_url,
                AttributeNames=['ApproximateNumberOfMessages']
            )
            
            attributes = response.get('Attributes', {})
            return {
                'failed_messages': int(attributes.get('ApproximateNumberOfMessages', 0))
            }
            
        except Exception as e:
            logger.error(f"Failed to get DLQ attributes: {e}")
            return {}
    
    def send_batch_messages(self, video_list: List[Dict]) -> Dict:
        """
        Send multiple video messages in a batch (up to 10 at a time)
        
        Args:
            video_list: List of video data dictionaries
        
        Returns:
            Dictionary with success/failure counts
        """
        if not video_list:
            return {"successful": 0, "failed": 0, "errors": []}
        
        # SQS batch limit is 10 messages
        batch_size = 10
        total_successful = 0
        total_failed = 0
        all_errors = []
        
        for i in range(0, len(video_list), batch_size):
            batch = video_list[i:i + batch_size]
            
            entries = []
            for idx, video_data in enumerate(batch):
                message_body = {
                    "video_id": video_data["id"],
                    "s3_key": video_data["s3_key"],
                    "run_id": video_data["run_id"],
                    "location_id": video_data["location_id"],
                    "started_at": video_data["started_at"],
                    "ended_at": video_data["ended_at"],
                    "enqueued_at": datetime.now().isoformat(),
                    "retry_count": 0
                }
                
                entries.append({
                    'Id': str(idx),
                    'MessageBody': json.dumps(message_body),
                    'MessageAttributes': {
                        'video_id': {
                            'StringValue': video_data["id"],
                            'DataType': 'String'
                        }
                    }
                })
            
            try:
                response = self.sqs.send_message_batch(
                    QueueUrl=self.queue_url,
                    Entries=entries
                )
                
                successful = len(response.get('Successful', []))
                failed = len(response.get('Failed', []))
                
                total_successful += successful
                total_failed += failed
                
                if failed > 0:
                    all_errors.extend(response.get('Failed', []))
                
                logger.info(f"Batch sent: {successful} successful, {failed} failed")
                
            except Exception as e:
                logger.error(f"Failed to send batch: {e}")
                total_failed += len(batch)
                all_errors.append({"error": str(e), "batch_size": len(batch)})
        
        return {
            "successful": total_successful,
            "failed": total_failed,
            "errors": all_errors
        }

def get_sqs_client(region: str, queue_url: str, dlq_url: str = None) -> SQSClient:
    """Factory function to create SQS client"""
    return SQSClient(region, queue_url, dlq_url)
