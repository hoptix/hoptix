# Hoptix Analytics Service

The Hoptix Analytics Service provides comprehensive reporting on upselling, upsizing, and add-on performance from transaction grading data.

## Features

- **Comprehensive Analytics**: Full breakdown of upsell, upsize, and add-on metrics
- **Item-Specific Analysis**: Performance metrics broken down by individual menu items
- **Time-Based Analysis**: Performance trends over time periods
- **Actionable Recommendations**: AI-generated suggestions for improvement
- **Multiple Output Formats**: JSON API endpoints and Python objects

## API Endpoints

### 1. Comprehensive Analytics
```
GET /analytics/comprehensive
```

**Parameters:**
- `run_id` (optional): Filter by specific run ID
- `date_from` (optional): Start date filter (YYYY-MM-DD)
- `date_to` (optional): End date filter (YYYY-MM-DD)
- `item_filter` (optional): Filter transactions containing specific items

**Example:**
```bash
curl "http://localhost:8000/analytics/comprehensive?run_id=12345"
```

### 2. Quick Summary
```
GET /analytics/summary
```

**Parameters:**
- `run_id` (optional): Filter by specific run ID

**Example:**
```bash
curl "http://localhost:8000/analytics/summary?run_id=12345"
```

### 3. Item-Specific Analytics
```
GET /analytics/items
```

**Parameters:**
- `run_id` (optional): Filter by specific run ID
- `limit` (optional): Number of top items to return (default: 20)

**Example:**
```bash
curl "http://localhost:8000/analytics/items?run_id=12345&limit=10"
```

## Response Format

### Comprehensive Analytics Response
```json
{
  "success": true,
  "data": {
    "summary": {
      "total_transactions": 100,
      "complete_transactions": 95,
      "completion_rate": 95.0,
      "avg_items_initial": 2.3,
      "avg_items_final": 2.8,
      "avg_item_increase": 0.5
    },
    "upselling": {
      "total_opportunities": 150,
      "total_offers": 120,
      "total_successes": 45,
      "success_rate": 37.5,
      "offer_rate": 80.0,
      "conversion_rate": 30.0,
      "by_item": {
        "22_1": {
          "opportunities": 20,
          "offers": 18,
          "successes": 8,
          "success_rate": 44.4,
          "offer_rate": 90.0
        }
      },
      "most_upsold_items": {
        "25_2": 15,
        "5_2": 12
      }
    },
    "upsizing": {
      "total_opportunities": 200,
      "total_offers": 160,
      "total_successes": 80,
      "success_rate": 50.0,
      "offer_rate": 80.0,
      "conversion_rate": 40.0,
      "largest_offer_rate": 85.0,
      "by_item": {...},
      "most_upsized_items": {...}
    },
    "addons": {
      "total_opportunities": 100,
      "total_offers": 70,
      "total_successes": 25,
      "success_rate": 35.7,
      "offer_rate": 70.0,
      "conversion_rate": 25.0,
      "by_item": {...},
      "most_successful_addons": {...}
    },
    "top_performing_items": {
      "most_frequent_items": {...},
      "highest_success_rate_items": {...},
      "most_successful_items": {...}
    },
    "recommendations": [
      "🎯 Upselling offer rate is only 45.2%. Train staff to identify and act on more upselling opportunities.",
      "📏 Upsizing offer rate is 67.8%. Encourage staff to suggest larger sizes more consistently."
    ]
  }
}
```

## Key Metrics Explained

### Upselling Metrics
- **Opportunities**: Number of times an upsell could have been offered
- **Offers**: Number of times an upsell was actually offered
- **Successes**: Number of successful upsells (customer accepted)
- **Success Rate**: Successes / Offers * 100
- **Offer Rate**: Offers / Opportunities * 100
- **Conversion Rate**: Successes / Opportunities * 100

### Upsizing Metrics
- **Largest Offer Rate**: Percentage of upsize offers that mentioned the largest option
- All other metrics same as upselling

### Add-on Metrics
- Same structure as upselling metrics
- Tracks additional toppings, sides, and extras

## Python Usage

```python
from services.analytics_service import HoptixAnalyticsService

# Initialize service
analytics = HoptixAnalyticsService()

# Load your transaction data (from CSV export or database)
transactions = [...]  # Your grading data

# Generate comprehensive report
report = analytics.generate_comprehensive_report(transactions)

# Get item-specific report
blizzard_report = analytics.get_item_specific_report(transactions, "blizzard")

# Access specific metrics
print(f"Upsell success rate: {report['upselling']['success_rate']:.1f}%")
print(f"Top recommendations: {report['recommendations'][:3]}")
```

## Data Input Format

The analytics service expects transaction data in the format exported by the grading CSV, with these key fields:

```json
{
  "Transaction ID": "uuid",
  "Date": "MM/DD/YYYY",
  "Complete Transcript?": 1,
  "Items Initially Requested": "[\"22_1\", \"36_1\"]",
  "# of Items Ordered": 2,
  "# of Chances to Upsell": 2,
  "# of Upselling Offers Made": 1,
  "# of Sucessfull Upselling chances": 1,
  "# of Chances to Upsize": 1,
  "# of Upsizing Offers Made": 1,
  "# of Sucessfull Upsizing chances": 0,
  "# of Chances to Add-on": 1,
  "# of Add-on Offers": 0,
  "# of Succesful Add-on Offers": 0
}
```

## Item Code Format

Items are referenced using the format `{ITEM_ID}_{SIZE_ID}`:
- `22_1`: Small Blizzard
- `22_2`: Medium Blizzard  
- `22_3`: Large Blizzard
- `36_1`: Single Burger
- `25_2`: Regular Fries

## Running the Example

```bash
cd hoptix-flask
python analytics_example.py
```

This will generate a sample report and save it to `analytics_report.json`.

## Integration with Your Workflow

1. **After CSV Export**: Use the `/analytics/comprehensive` endpoint to analyze your latest grading results
2. **Daily Reports**: Set up automated calls to `/analytics/summary` for daily performance tracking  
3. **Item Performance**: Use `/analytics/items` to identify which menu items need training focus
4. **Trend Analysis**: Use date filters to compare performance over time periods

## Performance Tips

- Use `run_id` filters to analyze specific batches of transactions
- Use `item_filter` to focus on specific menu categories
- The `limit` parameter helps manage response size for item analytics
- Cache results for frequently accessed reports
