from flask import Flask, request, jsonify
from supabase_client import supabase
from routes.auth import auth_bp
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.register_blueprint(auth_bp)


if __name__ == "__main__":
    app.run(debug=True)
