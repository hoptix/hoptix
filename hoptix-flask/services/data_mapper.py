#!/usr/bin/env python3
"""
Data mapping utilities for Hoptix Analytics

Converts database row format to analytics service expected format
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class AnalyticsDataMapper:
    """Maps database transaction data to analytics service expected format"""
    
    @staticmethod
    def map_transactions_for_analytics(db_transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert database transaction rows to format expected by HoptixAnalyticsService
        
        Args:
            db_transactions: List of transaction rows from graded_rows_filtered view
            
        Returns:
            List of transactions in CSV-style format expected by analytics service
        """
        logger.info(f"Mapping {len(db_transactions)} transactions for analytics processing")
        
        mapped_transactions = []
        
        for row in db_transactions:
            # Map database columns to CSV format expected by analytics service
            transaction = {
                "Transaction ID": row.get("transaction_id", ""),
                "Date": row.get("transaction_started_at", "").split("T")[0] if row.get("transaction_started_at") else "",
                "Complete Transcript?": row.get("complete_order", 0),
                "Items Initially Requested": row.get("items_initial", "0"),
                "# of Items Ordered": row.get("num_items_initial", 0),
                "# of Chances to Upsell": row.get("num_upsell_opportunities", 0),
                "upsell_candidate_items": row.get("upsell_candidate_items", "0"),
                "# of Upselling Offers Made": row.get("num_upsell_offers", 0),
                "upsell_offered_items": row.get("upsell_offered_items", "0"),
                "upsell_success_items": row.get("upsell_success_items", "0"),
                "# of Sucessfull Upselling chances": row.get("num_upsell_success", 0),
                "# of Times largest Option Offered": row.get("num_largest_offers", 0),
                "# of Chances to Upsize": row.get("num_upsize_opportunities", 0),
                "upsize_candidate_items": row.get("upsize_candidate_items", "0"),
                "# of Upsizing Offers Made": row.get("num_upsize_offers", 0),
                "upsize_offered_items": row.get("upsize_offered_items", "0"),
                "upsize_success_items": row.get("upsize_success_items", "0"),
                "# of Sucessfull Upsizing chances": row.get("num_upsize_success", 0),
                "# of Chances to Add-on": row.get("num_addon_opportunities", 0),
                "addon_candidate_items": row.get("addon_candidate_items", "0"),
                "# of Add-on Offers": row.get("num_addon_offers", 0),
                "addon_offered_items": row.get("addon_offered_items", "0"),
                "addon_success_items": row.get("addon_success_items", "0"),
                "# of Succesful Add-on Offers": row.get("num_addon_success", 0),
                "Items Ordered After Upsizing, Upselling, and Add-on Offers": row.get("items_after", "0"),
                "# of Items Ordered After Upselling, Upsizing, and Add-on Offers": row.get("num_items_after", 0),
                
                # Additional fields that might be useful
                "Employee ID": row.get("employee_id", ""),
                "Employee Name": row.get("employee_name", "Unknown"),
                "Operator": row.get("employee_name", "Unknown"),  # Analytics service expects "Operator" field
                "Video ID": row.get("video_id", ""),
                "Score": row.get("score", 0),
                "Feedback": row.get("feedback", ""),
                "Issues": row.get("issues", ""),
                "Mobile Order": row.get("mobile_order", 0),
                "Coupon Used": row.get("coupon_used", 0),
                "GPT Price": row.get("gpt_price", 0.0),
            }
            mapped_transactions.append(transaction)
        
        logger.info(f"Successfully mapped {len(mapped_transactions)} transactions")
        return mapped_transactions
