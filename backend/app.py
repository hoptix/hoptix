from flask import Flask
from flask_cors import CORS
from routes.analytics import analytics_bp

app = Flask(__name__)
CORS(app)
app.register_blueprint(analytics_bp)

@app.route("/")
def index():
    return "Hello, World!"

if __name__ == "__main__":
    app.run(debug=True, port=8000)