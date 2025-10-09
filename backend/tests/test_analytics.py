import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.analytics import Analytics


RUN_ID = "3afe854f-6cf6-403e-b2b2-77e039b6f8ca"
analytics = Analytics(RUN_ID)

# assert analytics.get_total_upsell_opportunities() == 135
# assert analytics.get_total_upsell_offers() == 29
# assert analytics.get_total_upsell_success() == 18
# assert analytics.get_total_upsize_opportunities() == 150   
# assert analytics.get_total_upsize_offers() == 35
# assert analytics.get_total_upsize_success() == 5
# assert analytics.get_total_addon_opportunities() == 288
# assert analytics.get_total_addon_offers() == 5
# assert analytics.get_total_addon_success() == 2

# Test item-level analytics
item_analytics = analytics.get_item_analytics()

analytics.upload_to_db()
# Print sample item data
# upload_to_db()
