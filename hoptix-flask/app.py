from flask import Flask
from config import Settings
from integrations.db_supabase import Supa

from routes.runs import runs_bp
from routes.videos import videos_bp

def create_app():
    app = Flask(__name__)
    s = Settings()
    app.config["SETTINGS"] = s
    app.config["DB"] = Supa(s.SUPABASE_URL, s.SUPABASE_SERVICE_KEY)

    app.register_blueprint(runs_bp, url_prefix="/runs")
    app.register_blueprint(videos_bp, url_prefix="/runs/<run_id>/videos")

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8000, debug=True)