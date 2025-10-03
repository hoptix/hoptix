#!/usr/bin/env python3
"""
Analytics API Routes for Hoptix

Provides REST API endpoints for accessing stored analytics data.
"""

from flask import Blueprint, request, jsonify
from integrations.db_supabase import Supa
from services.analytics_storage_service import AnalyticsStorageService
from services.analytics_service import HoptixAnalyticsService
from services.data_mapper import AnalyticsDataMapper
from services.item_lookup_service import ItemLookupService
from config import Settings
import logging
import json

logger = logging.getLogger(__name__)

# Create blueprint
analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')

# Initialize services
settings = Settings()
db = Supa(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
storage_service = AnalyticsStorageService(db)
# analytics_service will be created per request with location-specific data

def convert_item_ids_to_names(item_data, item_lookup: ItemLookupService) -> str:
    """Convert item IDs to human-readable names. Handles strings, lists, numbers, and None."""
    if not item_data or item_data in ['0', '[]', 'None', 'null', None, 0]:
        return 'None'
    
    try:
        # Handle different data types
        if isinstance(item_data, list):
            item_list = item_data
        elif isinstance(item_data, (int, float)):
            # Single numeric item ID
            item_list = [str(item_data)]
        elif isinstance(item_data, str):
            if item_data.startswith('[') and item_data.endswith(']'):
                # Parse as proper JSON array
                item_list = json.loads(item_data)
            else:
                # Single item or comma-separated
                item_list = [item_data.strip()]
        else:
            item_list = [str(item_data)]
        
        # Convert each item ID to name
        item_names = []
        for item_id in item_list:
            if item_id and str(item_id) != '0' and str(item_id).strip():
                item_name = item_lookup.get_item_name(str(item_id).strip())
                item_names.append(item_name)
        
        return ', '.join(item_names) if item_names else 'None'
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.warning(f"Failed to convert item data '{item_data}': {e}")
        return str(item_data)  # Return original if parsing fails

@analytics_bp.route('/run/<run_id>', methods=['GET'])
def get_run_analytics(run_id: str):
    """
    Get analytics results for a specific run
    
    Returns:
        JSON: Analytics data for the run
    """
    try:
        analytics = storage_service.get_run_analytics(run_id)
        
        if analytics:
            return jsonify({
                'success': True,
                'data': analytics
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Analytics not found for this run'
            }), 404
            
    except Exception as e:
        logger.error(f"Error retrieving run analytics: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@analytics_bp.route('/run/<run_id>/transactions', methods=['GET'])
def get_run_transactions(run_id: str):
    """
    Get raw transaction data for a specific run
    
    Query Parameters:
        limit (int): Number of transactions to return (default: 50, max: 200)
        offset (int): Number of transactions to skip for pagination (default: 0)
    
    Returns:
        JSON: Transaction data with pagination metadata
    """
    try:
        # Get query parameters
        limit = min(int(request.args.get('limit', 50)), 200)  # Cap at 200
        offset = max(int(request.args.get('offset', 0)), 0)   # Ensure non-negative
        
        # Get transactions directly from graded_rows_filtered view
        # Get count first
        count_result = db.client.table('graded_rows_filtered').select('transaction_id', count='exact').eq('run_id', run_id).execute()
        total_count = count_result.count if count_result.count is not None else 0
        
        # Get the actual data
        result = db.client.table('graded_rows_filtered').select('*').eq('run_id', run_id).order('begin_time', desc=True).range(offset, offset + limit - 1).execute()
        
        # Get location_id from first transaction to initialize item lookup
        location_id = None
        if result.data:
            # Try to get location_id from run
            run_result = db.client.table('runs').select('location_id').eq('id', run_id).execute()
            location_id = run_result.data[0].get('location_id') if run_result.data else None
        
        # Initialize item lookup service
        item_lookup = ItemLookupService(db, location_id) if location_id else ItemLookupService()
        
        # Process transactions to convert item IDs to names
        processed_transactions = []
        for transaction in result.data if result.data else []:
            # Convert item ID fields to human-readable names
            processed_transaction = transaction.copy()
            
            # List of fields that contain item IDs to convert
            item_fields = [
                'items_initial', 'items_after', 'upsell_candidate_items', 'upsell_offered_items',
                'upsell_success_items', 'upsize_candidate_items', 'upsize_offered_items',
                'upsize_success_items', 'addon_candidate_items', 'addon_offered_items',
                'addon_success_items'
            ]
            
            for field in item_fields:
                if field in processed_transaction:
                    # Save raw version first
                    raw_value = processed_transaction[field]
                    processed_transaction[f"{field}_raw"] = raw_value
                    # Then convert to names
                    converted_value = convert_item_ids_to_names(raw_value, item_lookup)
                    processed_transaction[field] = converted_value
                    logger.info(f"Converted {field}: {raw_value} -> {converted_value}")
                else:
                    logger.debug(f"Field {field} not found in transaction")
            
            processed_transactions.append(processed_transaction)
        
        # Format the result to match expected structure
        result = {
            'transactions': processed_transactions,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
            'has_more': total_count > (offset + limit)
        }
        
        if result['transactions'] or offset == 0:  # Return empty result for valid run, but not if offset is invalid
            return jsonify({
                'success': True,
                'data': result
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'No transactions found for this run'
            }), 404
            
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Invalid limit or offset parameter'
        }), 400
    except Exception as e:
        logger.error(f"Error retrieving transactions for run {run_id}: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@analytics_bp.route('/location/<location_id>', methods=['GET'])
def get_location_analytics(location_id: str):
    """
    Get recent analytics results for a location
    
    Query Parameters:
        limit (int): Maximum number of results (default: 10)
        
    Returns:
        JSON: List of analytics results for the location
    """
    try:
        limit = request.args.get('limit', 10, type=int)
        limit = min(limit, 100)  # Cap at 100 for performance
        
        analytics_list = storage_service.get_location_analytics(location_id, limit)
        
        return jsonify({
            'success': True,
            'data': analytics_list,
            'count': len(analytics_list)
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving location analytics: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@analytics_bp.route('/organization/<org_id>/summary', methods=['GET'])
def get_org_summary(org_id: str):
    """
    Get aggregated analytics summary for an organization
    
    Query Parameters:
        days (int): Number of days to look back (default: 30)
        
    Returns:
        JSON: Aggregated analytics summary
    """
    try:
        days = request.args.get('days', 30, type=int)
        days = min(days, 365)  # Cap at 1 year
        
        summary = storage_service.get_org_analytics_summary(org_id, days)
        
        return jsonify({
            'success': True,
            'data': summary
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving org summary: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@analytics_bp.route('/location/<location_id>/trends', methods=['GET'])
def get_location_trends(location_id: str):
    """
    Get analytics trends over time for a location
    
    Query Parameters:
        days (int): Number of days to look back (default: 30)
        
    Returns:
        JSON: Time series data for trending charts
    """
    try:
        days = request.args.get('days', 30, type=int)
        days = min(days, 365)  # Cap at 1 year
        
        trends = storage_service.get_analytics_trends(location_id, days)
        
        return jsonify({
            'success': True,
            'data': trends,
            'period_days': days
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving location trends: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@analytics_bp.route('/run/<run_id>/detailed', methods=['GET'])
def get_run_detailed_analytics(run_id: str):
    """
    Get detailed analytics (including operator breakdowns) for a specific run
    
    Returns:
        JSON: Detailed analytics including item-by-item and operator-by-operator data
    """
    try:
        analytics = storage_service.get_run_analytics(run_id)
        
        if not analytics:
            return jsonify({
                'success': False,
                'error': 'Analytics not found for this run'
            }), 404
        
        # Extract detailed analytics from the stored JSON
        detailed_analytics = analytics.get('detailed_analytics', {})
        
        # Structure the response for frontend consumption
        response_data = {
            'run_id': run_id,
            'run_date': analytics.get('run_date'),
            'location_id': analytics.get('location_id'),
            'org_id': analytics.get('org_id'),
            
            # Summary metrics
            'summary': {
                'total_transactions': analytics.get('total_transactions', 0),
                'complete_transactions': analytics.get('complete_transactions', 0),
                'completion_rate': analytics.get('completion_rate', 0),
                'total_revenue': analytics.get('total_revenue', 0),
                'overall_conversion_rate': analytics.get('overall_conversion_rate', 0)
            },
            
            # Category performance
            'categories': {
                'upselling': {
                    'opportunities': analytics.get('upsell_opportunities', 0),
                    'offers': analytics.get('upsell_offers', 0),
                    'successes': analytics.get('upsell_successes', 0),
                    'conversion_rate': analytics.get('upsell_conversion_rate', 0),
                    'revenue': analytics.get('upsell_revenue', 0)
                },
                'upsizing': {
                    'opportunities': analytics.get('upsize_opportunities', 0),
                    'offers': analytics.get('upsize_offers', 0),
                    'successes': analytics.get('upsize_successes', 0),
                    'conversion_rate': analytics.get('upsize_conversion_rate', 0),
                    'revenue': analytics.get('upsize_revenue', 0)
                },
                'addons': {
                    'opportunities': analytics.get('addon_opportunities', 0),
                    'offers': analytics.get('addon_offers', 0),
                    'successes': analytics.get('addon_successes', 0),
                    'conversion_rate': analytics.get('addon_conversion_rate', 0),
                    'revenue': analytics.get('addon_revenue', 0)
                }
            },
            
            # Detailed breakdowns (if available)
            'item_breakdowns': {
                'upselling': detailed_analytics.get('upselling', {}).get('by_item', {}),
                'upsizing': detailed_analytics.get('upsizing', {}).get('by_item', {}),
                'addons': detailed_analytics.get('addons', {}).get('by_item', {})
            },
            
            # Operator performance (if available)
            'operator_analytics': detailed_analytics.get('operator_analytics', {}),
            
            # Recommendations
            'recommendations': detailed_analytics.get('recommendations', [])
        }
        
        return jsonify({
            'success': True,
            'data': response_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving detailed run analytics: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@analytics_bp.route('/location/<location_id>/leaderboard', methods=['GET'])
def get_location_leaderboard(location_id: str):
    """
    Get operator performance leaderboard for a location
    
    Query Parameters:
        days (int): Number of days to look back (default: 30)
        metric (str): Metric to rank by (conversion_rate, revenue, total_successes)
        
    Returns:
        JSON: Operator rankings
    """
    try:
        days = request.args.get('days', 30, type=int)
        metric = request.args.get('metric', 'conversion_rate')
        
        # Get recent analytics for this location
        analytics_list = storage_service.get_location_analytics(location_id, 50)  # Get more for aggregation
        
        # Aggregate operator performance across runs
        operator_stats = {}
        
        for analytics in analytics_list:
            detailed = analytics.get('detailed_analytics', {})
            operator_analytics = detailed.get('operator_analytics', {})
            
            # Process each category
            for category in ['upselling', 'upsizing', 'addons']:
                category_data = operator_analytics.get(category, {})
                
                for operator, metrics in category_data.items():
                    if operator not in operator_stats:
                        operator_stats[operator] = {
                            'total_opportunities': 0,
                            'total_offers': 0,
                            'total_successes': 0,
                            'total_revenue': 0
                        }
                    
                    stats = operator_stats[operator]
                    stats['total_opportunities'] += metrics.get('total_opportunities', 0)
                    stats['total_offers'] += metrics.get('total_offers', 0)
                    stats['total_successes'] += metrics.get('total_successes', 0)
                    stats['total_revenue'] += metrics.get('total_revenue', 0)
        
        # Calculate final metrics and rank
        leaderboard = []
        for operator, stats in operator_stats.items():
            conversion_rate = (stats['total_successes'] / stats['total_opportunities'] * 100) if stats['total_opportunities'] > 0 else 0
            
            leaderboard.append({
                'operator': operator,
                'conversion_rate': round(conversion_rate, 2),
                'total_revenue': round(stats['total_revenue'], 2),
                'total_successes': stats['total_successes'],
                'total_opportunities': stats['total_opportunities'],
                'total_offers': stats['total_offers']
            })
        
        # Sort by requested metric
        if metric == 'conversion_rate':
            leaderboard.sort(key=lambda x: x['conversion_rate'], reverse=True)
        elif metric == 'revenue':
            leaderboard.sort(key=lambda x: x['total_revenue'], reverse=True)
        elif metric == 'total_successes':
            leaderboard.sort(key=lambda x: x['total_successes'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': leaderboard[:10],  # Top 10
            'metric': metric,
            'period_days': days
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving location leaderboard: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@analytics_bp.route('/run/<run_id>/generate', methods=['POST'])
def generate_run_analytics(run_id: str):
    """
    Generate comprehensive analytics for a specific run
    
    This endpoint:
    1. Fetches all graded transactions for the run
    2. Generates comprehensive analytics (summary + operator + item breakdowns)
    3. Stores results in run_analytics table
    4. Returns the generated analytics
    
    Returns:
        JSON: Generated analytics data
    """
    try:
        logger.info(f"Generating analytics for run {run_id}")
        
        # Get all graded transactions for this run using the graded_rows_filtered view
        transactions_result = db.client.table("graded_rows_filtered").select(
            "*"
        ).eq("run_id", run_id).execute()
        
        if not transactions_result.data:
            return jsonify({
                'success': False,
                'error': 'No graded transactions found for this run'
            }), 404
        
        transactions = transactions_result.data
        logger.info(f"Found {len(transactions)} graded transactions for run {run_id}")
        
        # Map transaction data to analytics service expected format
        mapped_transactions = AnalyticsDataMapper.map_transactions_for_analytics(transactions)
        logger.info(f"Mapped transactions for analytics processing")
        
        
        # Get location_id from run for location-specific analytics
        run_result = db.client.table('runs').select('location_id').eq('id', run_id).execute()
        location_id = run_result.data[0].get('location_id') if run_result.data else None
        
        # Create location-specific analytics service
        analytics_service = HoptixAnalyticsService(db, location_id)
        
        # Generate comprehensive analytics report
        analytics_report = analytics_service.generate_comprehensive_report(mapped_transactions)
        
        # Store the analytics in the database
        success = storage_service.store_run_analytics(run_id, analytics_report)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Analytics generated and stored for run {run_id}',
                'data': analytics_report,
                'transaction_count': len(transactions)
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to store analytics results'
            }), 500
            
    except Exception as e:
        logger.error(f"Error generating analytics for run {run_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@analytics_bp.route('/run/<run_id>/transactions/detailed', methods=['GET'])
def get_run_transactions_detailed(run_id: str):
    """
    Get all transactions (graded and raw) for a specific run
    
    Query Parameters:
        include_grades (bool): Include grade details (default: true)
        limit (int): Maximum number of results (default: 1000)
        offset (int): Offset for pagination (default: 0)
        
    Returns:
        JSON: List of transactions with optional grade data
    """
    try:
        include_grades = request.args.get('include_grades', 'true').lower() == 'true'
        limit = min(request.args.get('limit', 1000, type=int), 5000)  # Cap at 5000
        offset = request.args.get('offset', 0, type=int)
        
        if include_grades:
            # Use the graded_rows_filtered view for complete data
            result = db.client.table("graded_rows_filtered").select(
                "transaction_id, transcript, employee_id, employee_name, "
                "started_at, ended_at, video_id, "
                "items_initial, num_items_initial, items_after, num_items_after, "
                "num_upsell_opportunities, num_upsell_offers, num_upsell_success, "
                "num_upsize_opportunities, num_upsize_offers, num_upsize_success, "
                "num_addon_opportunities, num_addon_offers, num_addon_success, "
                "score, upsell_possible, upsell_offered, upsize_possible, upsize_offered, "
                "feedback, issues, complete_order, mobile_order, coupon_used, gpt_price"
            ).eq("run_id", run_id).range(offset, offset + limit - 1).execute()
        else:
            # Just get basic transaction data
            result = db.client.table("transactions").select(
                "id, started_at, ended_at, kind, meta, video_id, worker_id"
            ).eq("run_id", run_id).range(offset, offset + limit - 1).execute()
        
        transactions = result.data or []
        
        # Get total count for pagination
        count_result = db.client.table("transactions").select(
            "id", count="exact"
        ).eq("run_id", run_id).execute()
        
        total_count = count_result.count or 0
        
        return jsonify({
            'success': True,
            'data': transactions,
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_count
            },
            'include_grades': include_grades
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving transactions for run {run_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@analytics_bp.route('/run/<run_id>/comprehensive', methods=['GET'])
def get_comprehensive_run_analytics(run_id: str):
    """
    Get comprehensive analytics for a run (summary + operator + item breakdowns)
    
    This endpoint returns:
    - Summary metrics (conversion rates, revenue, etc.)
    - Operator-level performance breakdowns
    - Item-level performance analysis
    - Recommendations
    - Time-based trends
    
    If analytics don't exist, optionally generate them.
    
    Query Parameters:
        generate_if_missing (bool): Generate analytics if not found (default: false)
        
    Returns:
        JSON: Comprehensive analytics data
    """
    try:
        generate_if_missing = request.args.get('generate_if_missing', 'false').lower() == 'true'
        
        # Try to get existing analytics first
        analytics = storage_service.get_run_analytics(run_id)
        
        if not analytics and generate_if_missing:
            logger.info(f"Analytics not found for run {run_id}, generating...")
            
            # Generate analytics (same logic as generate endpoint)
            transactions_result = db.client.table("graded_rows_filtered").select(
                "*"
            ).eq("run_id", run_id).execute()
            
            if not transactions_result.data:
                return jsonify({
                    'success': False,
                    'error': 'No graded transactions found for this run'
                }), 404
            
            transactions = transactions_result.data
            
            # Map transaction data to analytics service expected format
            mapped_transactions = AnalyticsDataMapper.map_transactions_for_analytics(transactions)
            print(mapped_transactions)
            
            # Get location_id from first transaction for location-specific analytics
            location_id = transactions[0].get('location_id') if transactions else None
            
            # Create location-specific analytics service
            analytics_service = HoptixAnalyticsService(db, location_id)
            
            analytics_report = analytics_service.generate_comprehensive_report(mapped_transactions)
            
            # Store the generated analytics
            storage_service.store_run_analytics(run_id, analytics_report)
            
            # Retrieve the stored analytics (includes metadata)
            analytics = storage_service.get_run_analytics(run_id)
        
        if not analytics:
            return jsonify({
                'success': False,
                'error': 'Analytics not found for this run. Use generate_if_missing=true to create them.'
            }), 404
        
        # Extract and structure comprehensive data
        detailed_analytics = analytics.get('detailed_analytics', {})
        
        comprehensive_data = {
            'run_info': {
                'run_id': run_id,
                'run_date': analytics.get('run_date'),
                'location_id': analytics.get('location_id'),
                'org_id': analytics.get('org_id'),
                'generated_at': analytics.get('created_at'),
                'total_transactions': analytics.get('total_transactions', 0)
            },
            
            # High-level summary
            'summary': {
                'completion_rate': analytics.get('completion_rate', 0),
                'overall_conversion_rate': analytics.get('overall_conversion_rate', 0),
                'total_revenue': analytics.get('total_revenue', 0),
                'total_opportunities': analytics.get('total_opportunities', 0),
                'total_offers': analytics.get('total_offers', 0),
                'total_successes': analytics.get('total_successes', 0)
            },
            
            # Category breakdowns
            'categories': {
                'upselling': {
                    'opportunities': analytics.get('upsell_opportunities', 0),
                    'offers': analytics.get('upsell_offers', 0),
                    'successes': analytics.get('upsell_successes', 0),
                    'conversion_rate': analytics.get('upsell_conversion_rate', 0),
                    'revenue': analytics.get('upsell_revenue', 0),
                    'by_item': detailed_analytics.get('upselling', {}).get('by_item', {}),
                    'by_operator': detailed_analytics.get('operator_analytics', {}).get('upselling', {})
                },
                'upsizing': {
                    'opportunities': analytics.get('upsize_opportunities', 0),
                    'offers': analytics.get('upsize_offers', 0),
                    'successes': analytics.get('upsize_successes', 0),
                    'conversion_rate': analytics.get('upsize_conversion_rate', 0),
                    'revenue': analytics.get('upsize_revenue', 0),
                    'by_item': detailed_analytics.get('upsizing', {}).get('by_item', {}),
                    'by_operator': detailed_analytics.get('operator_analytics', {}).get('upsizing', {})
                },
                'addons': {
                    'opportunities': analytics.get('addon_opportunities', 0),
                    'offers': analytics.get('addon_offers', 0),
                    'successes': analytics.get('addon_successes', 0),
                    'conversion_rate': analytics.get('addon_conversion_rate', 0),
                    'revenue': analytics.get('addon_revenue', 0),
                    'by_item': detailed_analytics.get('addons', {}).get('by_item', {}),
                    'by_operator': detailed_analytics.get('operator_analytics', {}).get('addons', {})
                }
            },
            
            # Top performing items and operators
            'top_performers': {
                'items': detailed_analytics.get('top_performing_items', {}),
                'operators': _calculate_top_operators(detailed_analytics.get('operator_analytics', {}))
            },
            
            # Recommendations and insights
            'insights': {
                'recommendations': detailed_analytics.get('recommendations', []),
                'time_analysis': detailed_analytics.get('time_analysis', {})
            }
        }
        
        return jsonify({
            'success': True,
            'data': comprehensive_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving comprehensive analytics for run {run_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

def _calculate_top_operators(operator_analytics: dict) -> list:
    """Calculate top performing operators across all categories"""
    operator_totals = {}
    
    # Aggregate across all categories
    for category_data in operator_analytics.values():
        for operator, metrics in category_data.items():
            if operator not in operator_totals:
                operator_totals[operator] = {
                    'total_opportunities': 0,
                    'total_successes': 0,
                    'total_revenue': 0
                }
            
            operator_totals[operator]['total_opportunities'] += metrics.get('total_opportunities', 0)
            operator_totals[operator]['total_successes'] += metrics.get('total_successes', 0)
            operator_totals[operator]['total_revenue'] += metrics.get('total_revenue', 0)
    
    # Calculate conversion rates and sort
    top_operators = []
    for operator, totals in operator_totals.items():
        conversion_rate = (totals['total_successes'] / totals['total_opportunities'] * 100) if totals['total_opportunities'] > 0 else 0
        
        top_operators.append({
            'operator': operator,
            'conversion_rate': round(conversion_rate, 2),
            'total_revenue': round(totals['total_revenue'], 2),
            'total_opportunities': totals['total_opportunities'],
            'total_successes': totals['total_successes']
        })
    
    # Sort by conversion rate
    top_operators.sort(key=lambda x: x['conversion_rate'], reverse=True)
    return top_operators[:10]  # Top 10


@analytics_bp.route('/location/<location_id>/top-transactions/daily', methods=['GET'])
def get_top_daily_transactions(location_id):
    """
    AI-powered endpoint to find the top 5 transactions of the day.
    
    Criteria for "top" transactions:
    1. High overall score (weighted 40%)
    2. High upselling success rate (weighted 25%) 
    3. High upsizing success rate (weighted 20%)
    4. High add-on success rate (weighted 15%)
    
    Query params:
    - date: YYYY-MM-DD format (defaults to today)
    - limit: number of top transactions to return (default 5, max 20)
    """
    try:
        from datetime import datetime, timedelta
        import pytz
        
        # Get query parameters
        target_date = request.args.get('date')
        limit = min(int(request.args.get('limit', 5)), 20)  # Cap at 20
        
        # Default to today if no date provided
        if not target_date:
            target_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Finding top {limit} transactions for location {location_id} on {target_date}")
        
        # Convert date to start/end timestamps for the day
        start_date = f"{target_date} 00:00:00+00"
        end_date = f"{target_date} 23:59:59+00"
        
        # Query graded_rows_filtered for transactions on this date at this location
        # First get run_ids for this location and date
        runs_result = db.client.table('runs').select('id').eq('location_id', location_id).gte('created_at', start_date).lte('created_at', end_date).execute()
        
        if not runs_result.data:
            return jsonify({
                'success': True,
                'data': {
                    'date': target_date,
                    'location_id': location_id,
                    'top_transactions': [],
                    'total_transactions_analyzed': 0,
                    'criteria_explanation': "No transactions found for the specified date and location"
                }
            }), 200
        
        run_ids = [run['id'] for run in runs_result.data]
        
        # Get all transactions for these runs
        transactions_result = db.client.table('graded_rows_filtered').select(
            'transaction_id, run_id, employee_name, begin_time, end_time, transcript, '
            'score, num_upsell_offers, num_upsell_success, '
            'num_upsize_offers, num_upsize_success, '
            'num_addon_offers, num_addon_success, ' 
            'items_initial, items_after, feedback, '
            'complete_order, mobile_order, coupon_used'
        ).in_('run_id', run_ids).execute()
        
        if not transactions_result.data:
            return jsonify({
                'success': True,
                'data': {
                    'date': target_date,
                    'location_id': location_id,
                    'top_transactions': [],
                    'total_transactions_analyzed': 0,
                    'criteria_explanation': "No graded transactions found for the specified date and location"
                }
            }), 200
        
        # AI-powered scoring algorithm
        top_transactions = []
        
        for transaction in transactions_result.data:
            # Skip incomplete transactions
            if not transaction.get('complete_order', 0):
                continue
                
            # Calculate individual performance metrics
            base_score = float(transaction.get('score', 0))
            
            # Upselling performance
            upsell_offers = transaction.get('num_upsell_offers', 0)
            upsell_success = transaction.get('num_upsell_success', 0)
            upsell_rate = (upsell_success / upsell_offers * 100) if upsell_offers > 0 else 0
            
            # Upsizing performance  
            upsize_offers = transaction.get('num_upsize_offers', 0)
            upsize_success = transaction.get('num_upsize_success', 0)
            upsize_rate = (upsize_success / upsize_offers * 100) if upsize_offers > 0 else 0
            
            # Add-on performance
            addon_offers = transaction.get('num_addon_offers', 0)
            addon_success = transaction.get('num_addon_success', 0)
            addon_rate = (addon_success / addon_offers * 100) if addon_offers > 0 else 0
            
            # Weighted composite score (AI criteria)
            # Higher weight on base score and upselling as they have the most revenue impact
            composite_score = (
                base_score * 0.40 +           # Base performance score (40%)
                (upsell_rate / 100) * 0.25 +  # Upselling success (25%)
                (upsize_rate / 100) * 0.20 +  # Upsizing success (20%)
                (addon_rate / 100) * 0.15     # Add-on success (15%)
            )
            
            # Bonus points for exceptional performance
            total_offers = upsell_offers + upsize_offers + addon_offers
            if total_offers >= 5:  # High-offer transactions get bonus
                composite_score += 0.1
            
            # Calculate transaction duration for efficiency metric
            try:
                start_time = datetime.fromisoformat(transaction['begin_time'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(transaction['end_time'].replace('Z', '+00:00'))
                duration_seconds = (end_time - start_time).total_seconds()
                duration_minutes = duration_seconds / 60
            except:
                duration_minutes = 0
            
            # Efficiency bonus (shorter transactions with high performance get bonus)
            if composite_score > 0.7 and duration_minutes > 0 and duration_minutes < 3:
                composite_score += 0.05
            
            top_transactions.append({
                'transaction_id': transaction['transaction_id'],
                'run_id': transaction['run_id'],
                'employee_name': transaction.get('employee_name', 'Unknown'),
                'start_time': transaction['begin_time'],
                'end_time': transaction['end_time'],
                'duration_minutes': round(duration_minutes, 2) if duration_minutes > 0 else None,
                'composite_score': round(composite_score, 4),
                'base_score': base_score,
                'performance_metrics': {
                    'upselling': {
                        'offers': upsell_offers,
                        'successes': upsell_success,
                        'success_rate': round(upsell_rate, 1)
                    },
                    'upsizing': {
                        'offers': upsize_offers,
                        'successes': upsize_success,
                        'success_rate': round(upsize_rate, 1)
                    },
                    'addons': {
                        'offers': addon_offers,
                        'successes': addon_success,
                        'success_rate': round(addon_rate, 1)
                    }
                },
                'items_initial': transaction.get('items_initial', '[]'),
                'items_after': transaction.get('items_after', '[]'),
                'feedback': transaction.get('feedback', ''),
                'transcript_preview': (transaction.get('transcript', '') or '')[:200] + '...' if len(transaction.get('transcript', '') or '') > 200 else transaction.get('transcript', ''),
                'special_flags': {
                    'mobile_order': bool(transaction.get('mobile_order', 0)),
                    'coupon_used': bool(transaction.get('coupon_used', 0))
                }
            })
        
        # Sort by composite score and take top N
        top_transactions.sort(key=lambda x: x['composite_score'], reverse=True)
        top_transactions = top_transactions[:limit]
        
        # Add ranking
        for i, transaction in enumerate(top_transactions):
            transaction['rank'] = i + 1
            
        return jsonify({
            'success': True,
            'data': {
                'date': target_date,
                'location_id': location_id,
                'top_transactions': top_transactions,
                'total_transactions_analyzed': len(transactions_result.data),
                'complete_transactions_analyzed': len([t for t in transactions_result.data if t.get('complete_order', 0)]),
                'criteria_explanation': {
                    'algorithm': 'AI-powered composite scoring',
                    'weights': {
                        'base_score': '40% - Overall transaction performance',
                        'upselling_success': '25% - Revenue impact through upselling',
                        'upsizing_success': '20% - Customer satisfaction through upsizing',
                        'addon_success': '15% - Additional value creation'
                    },
                    'bonuses': [
                        'High-opportunity transactions (5+ opportunities): +0.1 bonus',
                        'Efficient high-performers (>70% score, <3 min duration): +0.05 bonus'
                    ]
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error finding top transactions for location {location_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500
