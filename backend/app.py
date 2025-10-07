from flask import Flask
from flask_cors import CORS
from routes.analytics import analytics_bp
from routes.runs import runs_bp
import logging
import sys

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Set Flask app logger level
app.logger.setLevel(logging.INFO)

app.register_blueprint(analytics_bp)
app.register_blueprint(runs_bp)

@app.route("/")
def index():
    app.logger.info("Health check endpoint accessed")
    return "Hello, World!"

@app.route("/health")
def health():
    app.logger.info("Health endpoint accessed")
    return {"status": "healthy", "service": "hoptix-backend"}

if __name__ == "__main__":
    app.run(debug=True, port=8000)