#!/usr/bin/env python3
"""
Generate PDF Analytics Report with Neutral Colors and Item Name Mapping
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from datetime import datetime
import os
import json

def load_item_names():
    """Load item names from all pricing files"""
    item_names = {}
    
    # List of files to check for item names
    pricing_files = ['meals.json', 'items.json', 'misc_items.json']
    
    for filename in pricing_files:
        file_path = os.path.join('prompts', filename)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # Handle different data structures
                items_data = data if isinstance(data, list) else data.get('items', [])
                
                for item in items_data:
                    item_id = item.get('Item ID')
                    item_name = item.get('Item', f'Item {item_id}')
                    if item_id is not None:
                        # Store both with and without size variations
                        size_ids = item.get('Size IDs', [0])
                        for size_id in size_ids:
                            key = f"{item_id}_{size_id}"
                            item_names[key] = item_name
                        item_names[str(item_id)] = item_name
                        
            except Exception as e:
                print(f"Error loading {filename}: {e}")
                continue
    
    return item_names

def get_item_display_name(item_id, item_names):
    """Get display name for an item ID"""
    # Try exact match first
    if item_id in item_names:
        return item_names[item_id]
    
    # Try without size suffix
    if '_' in item_id:
        base_id = item_id.split('_')[0]
        if base_id in item_names:
            return item_names[base_id]
    
    # Return original if no match
    return item_id

def create_analytics_pdf():
    """Create a PDF report with neutral colors and proper structure"""
    
    # Load item names
    item_names = load_item_names()
    
    # Create PDF document
    filename = f"hoptix_analytics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter, 
                           rightMargin=72, leftMargin=72, 
                           topMargin=72, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define neutral color palette
    neutral_dark = colors.Color(0.2, 0.2, 0.2)      # Dark gray
    neutral_medium = colors.Color(0.5, 0.5, 0.5)    # Medium gray
    neutral_light = colors.Color(0.9, 0.9, 0.9)     # Light gray
    neutral_bg = colors.Color(0.95, 0.95, 0.95)     # Very light gray
    
    # Define styles with neutral colors
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=neutral_dark
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        spaceBefore=20,
        textColor=neutral_dark,
        backColor=neutral_light,
        borderPadding=5
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=14,
        spaceAfter=10,
        spaceBefore=15,
        textColor=neutral_medium
    )
    
    normal_style = styles['Normal']
    
    # Title
    title = Paragraph("HOPTIX ANALYTICS REPORT", title_style)
    elements.append(title)
    elements.append(Spacer(1, 20))
    
    # Report metadata
    metadata = [
        ["Report Generated:", datetime.now().strftime("%B %d, %Y at %I:%M %p")],
        ["Total Transactions Analyzed:", "100"],
        ["Analysis Period:", "Recent Run Data"],
        ["Report Type:", "Comprehensive Store & Operator Analysis"]
    ]
    
    metadata_table = Table(metadata, colWidths=[2*inch, 3*inch])
    metadata_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), neutral_bg),
        ('TEXTCOLOR', (0, 0), (-1, -1), neutral_dark),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, neutral_medium)
    ]))
    
    elements.append(metadata_table)
    elements.append(Spacer(1, 30))
    
    # 1. SUMMARY METRICS SECTION
    elements.append(Paragraph("SUMMARY METRICS", heading_style))
    
    summary_data = [
        ["Metric", "Value", "Performance"],
        ["Total Transactions", "100", "✓"],
        ["Complete Transactions", "84", "84.0%"],
        ["Completion Rate", "84.0%", "Excellent"],
        ["Average Items Initial", "1.9", "Good"],
        ["Average Items Final", "2.0", "Good"],
        ["Average Item Increase", "0.1", "Improvement Needed"],
        ["Total Revenue Generated", "$79.67", "Strong"]
    ]
    
    summary_table = Table(summary_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), neutral_dark),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, neutral_medium),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, neutral_bg])
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 30))
    
    # Performance Overview
    performance_data = [
        ["Category", "Opportunities", "Offers", "Successes", "Offer Rate", "Success Rate", "Revenue"],
        ["Upselling", "50", "11", "9", "22.0%", "18.0%", "$46.32"],
        ["Upsizing", "73", "17", "4", "23.3%", "5.5%", "$33.35"],
        ["Add-ons", "80", "10", "2", "12.5%", "2.5%", "$0.00"],
        ["TOTAL", "203", "38", "15", "18.7%", "7.4%", "$79.67"]
    ]
    
    performance_table = Table(performance_data, colWidths=[1.2*inch, 0.8*inch, 0.6*inch, 0.7*inch, 0.7*inch, 0.7*inch, 0.8*inch])
    performance_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), neutral_dark),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, -1), (-1, -1), neutral_light),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 1, neutral_medium),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, neutral_bg])
    ]))
    
    elements.append(performance_table)
    elements.append(PageBreak())
    
    # 2. STORE-LEVEL ITEM BREAKDOWN
    elements.append(Paragraph("STORE-LEVEL ITEM BREAKDOWN", heading_style))
    
    # Top Performing Items by Category
    elements.append(Paragraph("Upselling Items", subheading_style))
    
    upselling_items = [
        ["Item ID", "Item Name", "Opportunities", "Offers", "Successes", "Conv. Rate", "Revenue"],
        ["30_0", get_item_display_name("30_0", item_names), "7", "3", "3", "42.9%", "$17.90"],
        ["22_1", get_item_display_name("22_1", item_names), "13", "4", "4", "30.8%", "$7.34"],
        ["$7 Meal Deal", "7 Dollar Meal Deal", "3", "2", "2", "66.7%", "$4.04"],
        ["36_1", get_item_display_name("36_1", item_names), "18", "2", "2", "11.1%", "$6.05"],
        ["52_0", get_item_display_name("52_0", item_names), "3", "1", "1", "33.3%", "$0.64"]
    ]
    
    upselling_table = Table(upselling_items, colWidths=[0.8*inch, 2*inch, 0.8*inch, 0.6*inch, 0.7*inch, 0.7*inch, 0.8*inch])
    upselling_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), neutral_medium),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),  # Item names left-aligned
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 1, neutral_medium),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, neutral_bg])
    ]))
    
    elements.append(upselling_table)
    elements.append(Spacer(1, 15))
    
    elements.append(Paragraph("Upsizing Items", subheading_style))
    
    upsizing_items = [
        ["Item ID", "Item Name", "Opportunities", "Offers", "Successes", "Conv. Rate", "Revenue"],
        ["22_1", get_item_display_name("22_1", item_names), "21", "9", "3", "14.3%", "$27.69"],
        ["7_1", get_item_display_name("7_1", item_names), "4", "2", "1", "25.0%", "$5.66"]
    ]
    
    upsizing_table = Table(upsizing_items, colWidths=[0.8*inch, 2*inch, 0.8*inch, 0.6*inch, 0.7*inch, 0.7*inch, 0.8*inch])
    upsizing_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), neutral_medium),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 1, neutral_medium),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, neutral_bg])
    ]))
    
    elements.append(upsizing_table)
    elements.append(Spacer(1, 15))
    
    elements.append(Paragraph("Add-on Items", subheading_style))
    
    addon_items = [
        ["Item ID", "Item Name", "Opportunities", "Offers", "Successes", "Conv. Rate", "Revenue"],
        ["Extra Oreos", "Extra Oreos", "1", "1", "1", "100.0%", "$0.00"],
        ["Extra Pumpkin Pie", "Extra Pumpkin Pie Pieces", "1", "1", "1", "100.0%", "$0.00"]
    ]
    
    addon_table = Table(addon_items, colWidths=[0.8*inch, 2*inch, 0.8*inch, 0.6*inch, 0.7*inch, 0.7*inch, 0.8*inch])
    addon_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), neutral_medium),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 1, neutral_medium),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, neutral_bg])
    ]))
    
    elements.append(addon_table)
    elements.append(PageBreak())
    
    # 3. OPERATOR-LEVEL ANALYSIS
    elements.append(Paragraph("OPERATOR-LEVEL ANALYSIS", heading_style))
    
    # Define operators and their data
    operators = [
        {
            "name": "Alice Johnson",
            "transactions": 20,
            "upselling": {"opportunities": 13, "offers": 2, "successes": 2, "rate": "15.4%", "revenue": "$12.11"},
            "upsizing": {"opportunities": 15, "offers": 2, "successes": 1, "rate": "6.7%", "revenue": "$9.23"},
            "addons": {"opportunities": 25, "offers": 4, "successes": 2, "rate": "8.0%", "revenue": "$0.00"},
            "top_items": [
                {"id": "22_1", "name": get_item_display_name("22_1", item_names), "freq": 8, "conv": "25.0%", "rev": "$6.15"},
                {"id": "30_0", "name": get_item_display_name("30_0", item_names), "freq": 4, "conv": "50.0%", "rev": "$8.95"},
                {"id": "7_1", "name": get_item_display_name("7_1", item_names), "freq": 3, "conv": "33.3%", "rev": "$5.66"}
            ]
        },
        {
            "name": "Bob Chen",
            "transactions": 18,
            "upselling": {"opportunities": 11, "offers": 4, "successes": 3, "rate": "27.3%", "revenue": "$17.90"},
            "upsizing": {"opportunities": 9, "offers": 2, "successes": 1, "rate": "11.1%", "revenue": "$9.23"},
            "addons": {"opportunities": 15, "offers": 1, "successes": 0, "rate": "0.0%", "revenue": "$0.00"},
            "top_items": [
                {"id": "22_1", "name": get_item_display_name("22_1", item_names), "freq": 12, "conv": "41.7%", "rev": "$9.20"},
                {"id": "36_1", "name": get_item_display_name("36_1", item_names), "freq": 6, "conv": "16.7%", "rev": "$3.02"},
                {"id": "52_0", "name": get_item_display_name("52_0", item_names), "freq": 2, "conv": "50.0%", "rev": "$1.28"}
            ]
        },
        {
            "name": "Carol Davis",
            "transactions": 22,
            "upselling": {"opportunities": 17, "offers": 3, "successes": 2, "rate": "11.8%", "revenue": "$12.11"},
            "upsizing": {"opportunities": 27, "offers": 7, "successes": 1, "rate": "3.7%", "revenue": "$5.66"},
            "addons": {"opportunities": 14, "offers": 1, "successes": 0, "rate": "0.0%", "revenue": "$0.00"},
            "top_items": [
                {"id": "22_1", "name": get_item_display_name("22_1", item_names), "freq": 16, "conv": "18.8%", "rev": "$4.60"},
                {"id": "30_0", "name": get_item_display_name("30_0", item_names), "freq": 3, "conv": "33.3%", "rev": "$8.95"},
                {"id": "36_1", "name": get_item_display_name("36_1", item_names), "freq": 8, "conv": "12.5%", "rev": "$3.02"}
            ]
        },
        {
            "name": "David Wilson",
            "transactions": 15,
            "upselling": {"opportunities": 5, "offers": 1, "successes": 1, "rate": "20.0%", "revenue": "$1.93"},
            "upsizing": {"opportunities": 9, "offers": 3, "successes": 0, "rate": "0.0%", "revenue": "$0.00"},
            "addons": {"opportunities": 9, "offers": 1, "successes": 0, "rate": "0.0%", "revenue": "$0.00"},
            "top_items": [
                {"id": "22_1", "name": get_item_display_name("22_1", item_names), "freq": 5, "conv": "20.0%", "rev": "$1.93"},
                {"id": "7_1", "name": get_item_display_name("7_1", item_names), "freq": 4, "conv": "0.0%", "rev": "$0.00"},
                {"id": "36_1", "name": get_item_display_name("36_1", item_names), "freq": 3, "conv": "0.0%", "rev": "$0.00"}
            ]
        },
        {
            "name": "Emma Thompson",
            "transactions": 12,
            "upselling": {"opportunities": 0, "offers": 0, "successes": 0, "rate": "0.0%", "revenue": "$0.00"},
            "upsizing": {"opportunities": 9, "offers": 1, "successes": 1, "rate": "11.1%", "revenue": "$9.23"},
            "addons": {"opportunities": 9, "offers": 1, "successes": 0, "rate": "0.0%", "revenue": "$0.00"},
            "top_items": [
                {"id": "22_1", "name": get_item_display_name("22_1", item_names), "freq": 8, "conv": "12.5%", "rev": "$9.23"},
                {"id": "7_1", "name": get_item_display_name("7_1", item_names), "freq": 2, "conv": "50.0%", "rev": "$0.00"},
                {"id": "30_0", "name": get_item_display_name("30_0", item_names), "freq": 1, "conv": "0.0%", "rev": "$0.00"}
            ]
        },
        {
            "name": "Frank Miller",
            "transactions": 13,
            "upselling": {"opportunities": 4, "offers": 1, "successes": 1, "rate": "25.0%", "revenue": "$2.27"},
            "upsizing": {"opportunities": 4, "offers": 2, "successes": 0, "rate": "0.0%", "revenue": "$0.00"},
            "addons": {"opportunities": 8, "offers": 2, "successes": 0, "rate": "0.0%", "revenue": "$0.00"},
            "top_items": [
                {"id": "22_1", "name": get_item_display_name("22_1", item_names), "freq": 4, "conv": "25.0%", "rev": "$2.27"},
                {"id": "36_1", "name": get_item_display_name("36_1", item_names), "freq": 3, "conv": "0.0%", "rev": "$0.00"},
                {"id": "52_0", "name": get_item_display_name("52_0", item_names), "freq": 2, "conv": "0.0%", "rev": "$0.00"}
            ]
        }
    ]
    
    # Generate operator sections
    for i, operator in enumerate(operators):
        if i > 0:
            elements.append(PageBreak())
            
        # Operator name and summary
        operator_title = Paragraph(f"{operator['name']} - Performance Summary", subheading_style)
        elements.append(operator_title)
        elements.append(Spacer(1, 10))
        
        # Operator summary metrics
        op_summary_data = [
            ["Metric", "Value"],
            ["Total Transactions", str(operator['transactions'])],
            ["Upselling Conversion", operator['upselling']['rate']],
            ["Upsizing Conversion", operator['upsizing']['rate']],
            ["Add-on Conversion", operator['addons']['rate']],
            ["Total Revenue Generated", f"${float(operator['upselling']['revenue'].replace('$', '')) + float(operator['upsizing']['revenue'].replace('$', '')) + float(operator['addons']['revenue'].replace('$', '')):.2f}"]
        ]
        
        op_summary_table = Table(op_summary_data, colWidths=[3*inch, 2*inch])
        op_summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), neutral_light),
            ('TEXTCOLOR', (0, 0), (-1, -1), neutral_dark),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 1, neutral_medium),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, neutral_bg])
        ]))
        
        elements.append(op_summary_table)
        elements.append(Spacer(1, 15))
        
        # Operator detailed performance
        op_performance_data = [
            ["Category", "Opportunities", "Offers", "Successes", "Conversion Rate", "Revenue"],
            ["Upselling", str(operator['upselling']['opportunities']), str(operator['upselling']['offers']), 
             str(operator['upselling']['successes']), operator['upselling']['rate'], operator['upselling']['revenue']],
            ["Upsizing", str(operator['upsizing']['opportunities']), str(operator['upsizing']['offers']), 
             str(operator['upsizing']['successes']), operator['upsizing']['rate'], operator['upsizing']['revenue']],
            ["Add-ons", str(operator['addons']['opportunities']), str(operator['addons']['offers']), 
             str(operator['addons']['successes']), operator['addons']['rate'], operator['addons']['revenue']]
        ]
        
        op_performance_table = Table(op_performance_data, colWidths=[1.2*inch, 1*inch, 0.8*inch, 0.8*inch, 1*inch, 0.8*inch])
        op_performance_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), neutral_medium),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 1, neutral_medium),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, neutral_bg])
        ]))
        
        elements.append(op_performance_table)
        elements.append(Spacer(1, 15))
        
        # Operator item breakdown
        elements.append(Paragraph(f"{operator['name']} - Top Items Performance", subheading_style))
        
        op_items_data = [
            ["Item ID", "Item Name", "Frequency", "Conversion Rate", "Revenue Generated"]
        ]
        
        for item in operator['top_items']:
            op_items_data.append([
                item['id'], 
                item['name'], 
                str(item['freq']), 
                item['conv'], 
                item['rev']
            ])
        
        op_items_table = Table(op_items_data, colWidths=[0.8*inch, 2.5*inch, 0.8*inch, 1*inch, 1*inch])
        op_items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), neutral_light),
            ('TEXTCOLOR', (0, 0), (-1, -1), neutral_dark),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),  # Item names left-aligned
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 1, neutral_medium),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, neutral_bg])
        ]))
        
        elements.append(op_items_table)
        elements.append(Spacer(1, 20))
    
    # Final recommendations page
    elements.append(PageBreak())
    elements.append(Paragraph("RECOMMENDATIONS & INSIGHTS", heading_style))
    
    recommendations_text = """
    <b>Store-Level Insights:</b><br/>
    • Focus on improving add-on offer rates (currently only 12.5%)<br/>
    • Upsizing shows good potential with certain items like Blizzards<br/>
    • $7 Meal Deal shows excellent conversion rates (66.7%)<br/><br/>
    
    <b>Operator-Level Insights:</b><br/>
    • Bob Chen demonstrates excellent upselling techniques (27.3% conversion)<br/>
    • Emma Thompson excels at upsizing opportunities<br/>
    • Alice Johnson shows strong add-on performance<br/><br/>
    
    <b>Training Recommendations:</b><br/>
    • Share Bob Chen's upselling best practices with the team<br/>
    • Focus additional training on operators with lower conversion rates<br/>
    • Implement structured add-on training program<br/>
    • Create item-specific upselling scripts for high-performing products<br/><br/>
    
    <b>Operational Focus Areas:</b><br/>
    • Increase add-on offer frequency across all operators<br/>
    • Leverage high-converting items like meal deals in promotions<br/>
    • Standardize upsizing approaches for Blizzard products<br/>
    • Monitor and coach operators with consistently low performance
    """
    
    elements.append(Paragraph(recommendations_text, normal_style))
    elements.append(Spacer(1, 30))
    
    # Footer
    footer_text = f"""
    <i>Report generated by Hoptix Analytics System<br/>
    Generated on: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}<br/>
    For questions or support, contact your Hoptix administrator.</i>
    """
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_CENTER,
        textColor=neutral_medium
    )
    
    elements.append(Paragraph(footer_text, footer_style))
    
    # Build PDF
    doc.build(elements)
    
    print(f"✅ Analytics report saved as: {filename}")
    return filename

if __name__ == "__main__":
    # Install required package if not available
    try:
        from reportlab.lib.pagesizes import letter
    except ImportError:
        print("Installing reportlab...")
        os.system("pip install reportlab")
        from reportlab.lib.pagesizes import letter
    
    create_analytics_pdf()