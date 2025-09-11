import os
import uuid
import logging
from datetime import datetime
from flask import Flask, jsonify, request
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our modules
from config import Settings
from integrations.db_supabase import Supa

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('flask_app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize database connection
try:
    settings = Settings()
    db = Supa(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    app.config["DB"] = db
    logger.info("Successfully initialized database connection")
except Exception as e:
    logger.error(f"Failed to initialize database connection: {e}")
    raise

@app.get("/health")
def health():
    """Health check endpoint"""
    return jsonify({
        "ok": True, 
        "timestamp": datetime.now().isoformat(),
        "service": "hoptix-onboarding"
    })

@app.post("/onboard-restaurant")
def onboard_restaurant():
    """Onboard a new restaurant onto the Hoptix platform"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "JSON data required"
            }), 400
        
        # Validate required fields
        required_fields = ["restaurant_name", "location_name", "timezone"]
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({
                "success": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400
        
        restaurant_name = data["restaurant_name"]
        location_name = data["location_name"]
        timezone = data["timezone"]
        
        logger.info(f"Onboarding restaurant: {restaurant_name} - {location_name}")
        
        # Generate IDs
        org_id = str(uuid.uuid4())
        location_id = str(uuid.uuid4())
        
        # Create organization
        org_data = {
            "id": org_id,
            "name": restaurant_name,
            "created_at": datetime.now().isoformat()
        }
        db.client.table("orgs").insert(org_data).execute()
        logger.info(f"Created organization: {org_id}")
        
        # Create location
        location_data = {
            "id": location_id,
            "org_id": org_id,
            "name": location_name,
            "tz": timezone,
            "created_at": datetime.now().isoformat()
        }
        db.client.table("locations").insert(location_data).execute()
        logger.info(f"Created location: {location_id}")
        
        result = {
            "success": True,
            "message": f"Successfully onboarded {restaurant_name} - {location_name}",
            "data": {
                "org_id": org_id,
                "location_id": location_id,
                "restaurant_name": restaurant_name,
                "location_name": location_name,
                "timezone": timezone
            }
        }
        
        logger.info(f"Successfully onboarded restaurant: {org_id} / {location_id}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error onboarding restaurant: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)