import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.analytics import Analytics


RUN_ID = "fdfe9f1f-b64f-4891-ace2-9b16ad08c57c"

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
item_analytics = analytics.upload_to_db()
print(f"Uploaded {len(item_analytics)} items in analytics")

# Print sample item data
# upload_to_db()
