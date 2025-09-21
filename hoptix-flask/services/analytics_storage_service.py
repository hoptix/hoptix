#!/usr/bin/env python3
"""
Analytics Storage Service for Hoptix

This service handles storing and retrieving analytics results from the database.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from integrations.db_supabase import Supa

logger = logging.getLogger(__name__)

class AnalyticsStorageService:
    """Service for storing and retrieving analytics results"""
    
    def __init__(self, db: Supa):
        self.db = db
    
    def store_run_analytics(self, run_id: str, analytics_report: Dict[str, Any]) -> bool:
        """
        Store analytics results for a run
        
        Args:
            run_id: The run ID to store analytics for
            analytics_report: The complete analytics report from HoptixAnalyticsService
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Extract key metrics from the report
            summary = analytics_report.get('summary', {})
            upselling = analytics_report.get('upselling', {})
            upsizing = analytics_report.get('upsizing', {})
            addons = analytics_report.get('addons', {})
            
            # Calculate totals
            total_opportunities = (
                upselling.get('total_opportunities', 0) +
                upsizing.get('total_opportunities', 0) +
                addons.get('total_opportunities', 0)
            )
            total_offers = (
                upselling.get('total_offers', 0) +
                upsizing.get('total_offers', 0) +
                addons.get('total_offers', 0)
            )
            total_successes = (
                upselling.get('total_successes', 0) +
                upsizing.get('total_successes', 0) +
                addons.get('total_successes', 0)
            )
            total_revenue = (
                upselling.get('total_revenue', 0) +
                upsizing.get('total_revenue', 0) +
                addons.get('total_revenue', 0)
            )
            overall_conversion_rate = (total_successes / total_opportunities * 100) if total_opportunities > 0 else 0
            
            # Prepare data for insertion
            analytics_data = {
                'run_id': run_id,
                
                # Summary metrics
                'total_transactions': summary.get('total_transactions', 0),
                'complete_transactions': summary.get('complete_transactions', 0),
                'completion_rate': round(summary.get('completion_rate', 0), 2),
                'avg_items_initial': round(summary.get('avg_items_initial', 0), 2),
                'avg_items_final': round(summary.get('avg_items_final', 0), 2),
                'avg_item_increase': round(summary.get('avg_item_increase', 0), 2),
                
                # Upselling metrics
                'upsell_opportunities': upselling.get('total_opportunities', 0),
                'upsell_offers': upselling.get('total_offers', 0),
                'upsell_successes': upselling.get('total_successes', 0),
                'upsell_conversion_rate': round(upselling.get('conversion_rate', 0), 2),
                'upsell_revenue': round(upselling.get('total_revenue', 0), 2),
                
                # Upsizing metrics
                'upsize_opportunities': upsizing.get('total_opportunities', 0),
                'upsize_offers': upsizing.get('total_offers', 0),
                'upsize_successes': upsizing.get('total_successes', 0),
                'upsize_conversion_rate': round(upsizing.get('conversion_rate', 0), 2),
                'upsize_revenue': round(upsizing.get('total_revenue', 0), 2),
                
                # Add-on metrics
                'addon_opportunities': addons.get('total_opportunities', 0),
                'addon_offers': addons.get('total_offers', 0),
                'addon_successes': addons.get('total_successes', 0),
                'addon_conversion_rate': round(addons.get('conversion_rate', 0), 2),
                'addon_revenue': round(addons.get('total_revenue', 0), 2),
                
                # Overall performance
                'total_opportunities': total_opportunities,
                'total_offers': total_offers,
                'total_successes': total_successes,
                'overall_conversion_rate': round(overall_conversion_rate, 2),
                'total_revenue': round(total_revenue, 2),
                
                # Store complete report as JSON for detailed analysis
                'detailed_analytics': analytics_report
            }
            
            # Use upsert to handle potential duplicates
            result = self.db.client.table('run_analytics').upsert(
                analytics_data,
                on_conflict='run_id'
            ).execute()
            
            if result.data:
                logger.info(f"Successfully stored analytics for run {run_id}")
                return True
            else:
                logger.error(f"Failed to store analytics for run {run_id}: No data returned")
                return False
                
        except Exception as e:
            logger.error(f"Error storing analytics for run {run_id}: {e}")
            return False
    
    def get_run_analytics(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get analytics results for a specific run
        
        Args:
            run_id: The run ID to get analytics for
            
        Returns:
            Dict containing analytics data or None if not found
        """
        try:
            result = self.db.client.table('run_analytics_with_details').select('*').eq('run_id', run_id).execute()
            
            if result.data:
                return result.data[0]
            else:
                logger.warning(f"No analytics found for run {run_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving analytics for run {run_id}: {e}")
            return None
    
    def get_location_analytics(self, location_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent analytics results for a location
        
        Args:
            location_id: The location ID to get analytics for
            limit: Maximum number of results to return
            
        Returns:
            List of analytics results ordered by run_date desc
        """
        try:
            result = self.db.client.table('run_analytics_with_details')\
                .select('*')\
                .eq('location_id', location_id)\
                .order('run_date', desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error retrieving location analytics for {location_id}: {e}")
            return []
    
    def get_org_analytics_summary(self, org_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get aggregated analytics summary for an organization
        
        Args:
            org_id: The organization ID
            days: Number of days to look back
            
        Returns:
            Dict containing aggregated metrics
        """
        try:
            # Get analytics for the last N days
            result = self.db.client.table('run_analytics_with_details')\
                .select('*')\
                .eq('org_id', org_id)\
                .gte('run_date', f'now() - interval \'{days} days\'')\
                .execute()
            
            if not result.data:
                return {
                    'total_runs': 0,
                    'total_transactions': 0,
                    'avg_completion_rate': 0,
                    'avg_conversion_rate': 0,
                    'total_revenue': 0,
                    'period_days': days
                }
            
            # Aggregate the data
            analytics_list = result.data
            total_runs = len(analytics_list)
            
            # Sum up all metrics
            total_transactions = sum(a.get('total_transactions', 0) for a in analytics_list)
            total_complete = sum(a.get('complete_transactions', 0) for a in analytics_list)
            total_opportunities = sum(a.get('total_opportunities', 0) for a in analytics_list)
            total_successes = sum(a.get('total_successes', 0) for a in analytics_list)
            total_revenue = sum(a.get('total_revenue', 0) for a in analytics_list)
            
            # Calculate averages
            avg_completion_rate = (total_complete / total_transactions * 100) if total_transactions > 0 else 0
            avg_conversion_rate = (total_successes / total_opportunities * 100) if total_opportunities > 0 else 0
            
            return {
                'total_runs': total_runs,
                'total_transactions': total_transactions,
                'avg_completion_rate': round(avg_completion_rate, 2),
                'avg_conversion_rate': round(avg_conversion_rate, 2),
                'total_revenue': round(total_revenue, 2),
                'period_days': days,
                'avg_revenue_per_run': round(total_revenue / total_runs, 2) if total_runs > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error retrieving org analytics summary for {org_id}: {e}")
            return {
                'total_runs': 0,
                'total_transactions': 0,
                'avg_completion_rate': 0,
                'avg_conversion_rate': 0,
                'total_revenue': 0,
                'period_days': days,
                'error': str(e)
            }
    
    def get_analytics_trends(self, location_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get analytics trends over time for a location
        
        Args:
            location_id: The location ID
            days: Number of days to look back
            
        Returns:
            List of daily analytics data for trending
        """
        try:
            result = self.db.client.table('run_analytics_with_details')\
                .select('run_date, completion_rate, overall_conversion_rate, total_revenue, total_transactions')\
                .eq('location_id', location_id)\
                .gte('run_date', f'now() - interval \'{days} days\'')\
                .order('run_date', desc=False)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error retrieving analytics trends for {location_id}: {e}")
            return []



