#!/usr/bin/env python3
"""
Example usage of the Hoptix Analytics Service

This script demonstrates how to use the analytics service with your grading data.
"""

import json
from services.analytics_service import HoptixAnalyticsService

def main():
    # Load data from the graded_rows_filtered.json file
    with open('/Users/ronitjain/Desktop/Hoptix/hoptix-flask/graded_rows_filtered_rows.json', 'r') as f:
        sample_data = json.load(f)
    
    # Initialize the analytics service
    analytics_service = HoptixAnalyticsService()
    
    # Generate comprehensive report
    print("🔍 Generating comprehensive analytics report...\n")
    report = analytics_service.generate_comprehensive_report(sample_data)
    
    # Display summary
    print("📊 SUMMARY METRICS")
    print("=" * 50)
    summary = report["summary"]
    print(f"Total Transactions: {summary['total_transactions']}")
    print(f"Complete Transactions: {summary['complete_transactions']}")
    print(f"Completion Rate: {summary['completion_rate']:.1f}%")
    print(f"Avg Items Initial: {summary['avg_items_initial']:.1f}")
    print(f"Avg Items Final: {summary['avg_items_final']:.1f}")
    print(f"Avg Item Increase: {summary['avg_item_increase']:.1f}")
    
    # Display upselling metrics
    print("\n🎯 UPSELLING METRICS")
    print("=" * 50)
    upselling = report["upselling"]
    print(f"Opportunities: {upselling['total_opportunities']}")
    print(f"Offers: {upselling['total_offers']}")
    print(f"Successes: {upselling['total_successes']}")
    print(f"Conversion Rate: {upselling['conversion_rate']:.1f}%")
    print(f"Revenue Generated: ${upselling.get('total_revenue', 0):.2f}")
    
    # Show item-specific upsell performance
    if upselling.get('by_item'):
        print("\nItem Breakdown:")
        sorted_items = sorted(upselling['by_item'].items(), 
                            key=lambda x: x[1]['successes'], reverse=True)
        for item, metrics in sorted_items:
            if metrics['successes'] > 0:
                conversion_rate = (metrics['successes'] / metrics['opportunities'] * 100) if metrics['opportunities'] > 0 else 0
                print(f"  • {item}:")
                print(f"    - Opportunities: {metrics['opportunities']}")
                print(f"    - Offers: {metrics['offers']}")
                print(f"    - Successes: {metrics['successes']}")
                print(f"    - Conversion Rate: {conversion_rate:.1f}%")
                print(f"    - Revenue Generated: ${metrics.get('revenue', 0):.2f}")
    
    # Display upsizing metrics
    print("\n📏 UPSIZING METRICS")
    print("=" * 50)
    upsizing = report["upsizing"]
    print(f"Opportunities: {upsizing['total_opportunities']}")
    print(f"Offers: {upsizing['total_offers']}")
    print(f"Successes: {upsizing['total_successes']}")
    print(f"Conversion Rate: {upsizing['conversion_rate']:.1f}%")
    print(f"Revenue Generated: ${upsizing.get('total_revenue', 0):.2f}")
    
    # Show item-specific upsize performance
    if upsizing.get('by_item'):
        print("\nItem Breakdown:")
        sorted_items = sorted(upsizing['by_item'].items(), 
                            key=lambda x: x[1]['successes'], reverse=True)
        for item, metrics in sorted_items:
            if metrics['successes'] > 0:
                conversion_rate = (metrics['successes'] / metrics['opportunities'] * 100) if metrics['opportunities'] > 0 else 0
                print(f"  • {item}:")
                print(f"    - Opportunities: {metrics['opportunities']}")
                print(f"    - Offers: {metrics['offers']}")
                print(f"    - Successes: {metrics['successes']}")
                print(f"    - Conversion Rate: {conversion_rate:.1f}%")
                print(f"    - Revenue Generated: ${metrics.get('revenue', 0):.2f}")
    
    # Display add-on metrics
    print("\n🍟 ADD-ON METRICS")
    print("=" * 50)
    addons = report["addons"]
    print(f"Opportunities: {addons['total_opportunities']}")
    print(f"Offers: {addons['total_offers']}")
    print(f"Successes: {addons['total_successes']}")
    print(f"Conversion Rate: {addons['conversion_rate']:.1f}%")
    print(f"Revenue Generated: ${addons.get('total_revenue', 0):.2f}")
    
    # Show item-specific add-on performance
    if addons.get('by_item'):
        print("\nItem Breakdown:")
        sorted_items = sorted(addons['by_item'].items(), 
                            key=lambda x: x[1]['successes'], reverse=True)
        for item, metrics in sorted_items:
            if metrics['successes'] > 0:
                conversion_rate = (metrics['successes'] / metrics['opportunities'] * 100) if metrics['opportunities'] > 0 else 0
                print(f"  • {item}:")
                print(f"    - Opportunities: {metrics['opportunities']}")
                print(f"    - Offers: {metrics['offers']}")
                print(f"    - Successes: {metrics['successes']}")
                print(f"    - Conversion Rate: {conversion_rate:.1f}%")
                print(f"    - Revenue Generated: ${metrics.get('revenue', 0):.2f}")
    
    # Display top performing items
    print("\n⭐ TOP PERFORMING ITEMS")
    print("=" * 50)
    top_items = report["top_performing_items"]
    print("Most Frequent Items:")
    most_frequent = top_items["most_frequent_items"]
    if isinstance(most_frequent, dict):
        # Handle dict format
        for item, stats in list(most_frequent.items())[:3]:
            freq = stats.get('frequency', stats) if isinstance(stats, dict) else stats
            print(f"  • {item}: {freq} transactions")
    elif isinstance(most_frequent, list):
        # Handle list of tuples format
        for item, stats in most_frequent[:3]:
            freq = stats.get('frequency', stats) if isinstance(stats, dict) else stats
            print(f"  • {item}: {freq} transactions")
    else:
        print("  No frequent items data available")
    
    # Display operator-level analytics
    print("\n👥 OPERATOR-LEVEL ANALYTICS")
    print("=" * 50)
    
    operator_analytics = report.get("operator_analytics", {})
    
    # Upselling by operator
    print("\n🎯 UPSELLING BY OPERATOR")
    print("-" * 30)
    upselling_by_op = operator_analytics.get("upselling", {})
    if upselling_by_op:
        # Sort operators by success rate
        sorted_operators = sorted(upselling_by_op.items(), 
                                key=lambda x: x[1]['success_rate'], reverse=True)
        for operator, metrics in sorted_operators:
            print(f"{operator}:")
            print(f"  • Opportunities: {metrics['total_opportunities']}")
            print(f"  • Offers: {metrics['total_offers']}")
            print(f"  • Successes: {metrics['total_successes']}")
            print(f"  • Conversion Rate: {metrics['conversion_rate']:.1f}%")
            print(f"  • Revenue Generated: ${metrics.get('total_revenue', 0):.2f}")
            print()
    else:
        print("No operator upselling data available")
    
    # Upsizing by operator
    print("\n📏 UPSIZING BY OPERATOR")
    print("-" * 30)
    upsizing_by_op = operator_analytics.get("upsizing", {})
    if upsizing_by_op:
        sorted_operators = sorted(upsizing_by_op.items(), 
                                key=lambda x: x[1]['success_rate'], reverse=True)
        for operator, metrics in sorted_operators:
            print(f"{operator}:")
            print(f"  • Opportunities: {metrics['total_opportunities']}")
            print(f"  • Offers: {metrics['total_offers']}")
            print(f"  • Successes: {metrics['total_successes']}")
            print(f"  • Conversion Rate: {metrics['conversion_rate']:.1f}%")
            print(f"  • Revenue Generated: ${metrics.get('total_revenue', 0):.2f}")
            print()
    else:
        print("No operator upsizing data available")
    
    # Add-ons by operator
    print("\n🍟 ADD-ONS BY OPERATOR")
    print("-" * 30)
    addons_by_op = operator_analytics.get("addons", {})
    if addons_by_op:
        sorted_operators = sorted(addons_by_op.items(), 
                                key=lambda x: x[1]['success_rate'], reverse=True)
        for operator, metrics in sorted_operators:
            print(f"{operator}:")
            print(f"  • Opportunities: {metrics['total_opportunities']}")
            print(f"  • Offers: {metrics['total_offers']}")
            print(f"  • Successes: {metrics['total_successes']}")
            print(f"  • Conversion Rate: {metrics['conversion_rate']:.1f}%")
            print(f"  • Revenue Generated: ${metrics.get('total_revenue', 0):.2f}")
            print()
    else:
        print("No operator add-on data available")
    
    # Display recommendations
    print("\n💡 RECOMMENDATIONS")
    print("=" * 50)
    for i, rec in enumerate(report["recommendations"], 1):
        print(f"{i}. {rec}")
    
    # Example: Get item-specific report for Blizzards
    print("\n\n🍦 BLIZZARD-SPECIFIC ANALYTICS")
    print("=" * 50)
    blizzard_report = analytics_service.get_item_specific_report(sample_data, "22_")
    blizzard_summary = blizzard_report["summary"]
    print(f"Blizzard Transactions: {blizzard_summary['total_transactions']}")
    print(f"Avg Items per Transaction: {blizzard_summary['avg_items_final']:.1f}")
    
    # Show Blizzard upselling performance
    blizzard_upselling = blizzard_report["upselling"]
    print(f"\nBlizzard Upselling:")
    print(f"  • Opportunities: {blizzard_upselling['total_opportunities']}")
    print(f"  • Success Rate: {blizzard_upselling['success_rate']:.1f}%")
    print(f"  • Revenue: ${blizzard_upselling.get('total_revenue', 0):.2f}")
    
    # Show Blizzard add-on performance
    blizzard_addons = blizzard_report["addons"]
    print(f"\nBlizzard Add-Ons:")
    print(f"  • Opportunities: {blizzard_addons['total_opportunities']}")
    print(f"  • Success Rate: {blizzard_addons['success_rate']:.1f}%")
    print(f"  • Most Successful Add-Ons: {list(blizzard_addons.get('most_successful_addons', {}).keys())[:3]}")
    
    # Show Blizzard upsizing performance
    blizzard_upsizing = blizzard_report["upsizing"]
    print(f"\nBlizzard Upsizing:")
    print(f"  • Opportunities: {blizzard_upsizing['total_opportunities']}")
    print(f"  • Success Rate: {blizzard_upsizing['success_rate']:.1f}%")
    print(f"  • Most Upsized Items: {list(blizzard_upsizing.get('most_upsized_items', {}).keys())[:3]}")
    
    # Save full report to JSON file
    with open("analytics_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n💾 Full report saved to analytics_report.json")

if __name__ == "__main__":
    main()
