from flask import Flask
from flask_cors import CORS
from routes.analytics import analytics_bp
from routes.runs import runs_bp


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.register_blueprint(analytics_bp)
app.register_blueprint(runs_bp)

@app.route("/")
def index():
    return "Hello, World!"

if __name__ == "__main__":
    app.run(debug=True, port=8000)