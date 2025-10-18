import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.analytics import Analytics
from services.database import Supa

db = Supa()
run_Ids = db.client.table("runs").select("id").execute().data   
for run_id in run_Ids:
    analytics = Analytics(run_id["id"])
    item_analytics, revenue_map = analytics.get_item_analytics()
    analytics.upload_to_db()

# assert analytics.get_total_upsell_opportunities() == 135
# assert analytics.get_total_upsell_offers() == 29
# assert analytics.get_total_upsell_success() == 18
# assert analytics.get_total_upsize_opportunities() == 150   
# assert analytics.get_total_upsize_offers() == 35
# assert analytics.get_total_upsize_success() == 5
# assert analytics.get_total_addon_opportunities() == 288
# assert analytics.get_total_addon_offers() == 5
# assert analytics.get_total_addon_success() == 2
