#!/usr/bin/env python3
"""
Generate AI feedback for all operators in the workers table.
This script fetches all operator IDs and generates monthly feedback for each one.
"""

import sys
import os
from datetime import datetime

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.database import Supa
from services.ai_feedback import get_ai_feedback
from config import Settings

def main():
    """Generate AI feedback for all operators"""
    print("🚀 Starting AI feedback generation for all operators...")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Initialize services
        settings = Settings()
        db = Supa()
        
        # Get all operator IDs from workers table
        print("📋 Fetching all operator IDs from workers table...")
        result = db.client.table("workers").select("id").execute()
        
        if not result.data:
            print("❌ No operators found in workers table")
            return
        
        operator_ids = [worker["id"] for worker in result.data]
        print(f"✅ Found {len(operator_ids)} operators")
        
        # Process each operator
        successful = 0
        failed = 0
        
        for i, operator_id in enumerate(operator_ids, 1):
            print(f"\n🎯 Processing operator {i}/{len(operator_ids)}: {operator_id}")
            
            try:
                # Generate AI feedback with timeout
                import signal
                
                def timeout_handler(signum, frame):
                    raise TimeoutError("AI feedback generation timed out")
                
                # Set 5 minute timeout
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(300)  # 5 minutes
                
                try:
                    feedback = get_ai_feedback(operator_id)
                    signal.alarm(0)  # Cancel timeout
                    
                    if feedback:
                        # Store the feedback in the database
                        db.insert_operator_feedback(operator_id, str(feedback))
                        print(f"✅ Generated and stored feedback for operator {operator_id}")
                        successful += 1
                    else:
                        print(f"⚠️ No feedback generated for operator {operator_id}")
                        failed += 1
                        
                except TimeoutError:
                    print(f"⏰ Timeout: AI feedback generation took too long for operator {operator_id}")
                    failed += 1
                    
            except Exception as e:
                print(f"❌ Failed to process operator {operator_id}: {e}")
                failed += 1
                continue
        
        # Summary
        print(f"\n🎉 AI feedback generation completed!")
        print(f"📊 Results:")
        print(f"   - Total operators: {len(operator_ids)}")
        print(f"   - Successful: {successful}")
        print(f"   - Failed: {failed}")
        print(f"   - Success rate: {(successful/len(operator_ids)*100):.1f}%")
        print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"💥 Script failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
