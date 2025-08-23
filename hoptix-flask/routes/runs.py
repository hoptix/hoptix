from flask import Blueprint, current_app, request

runs_bp = Blueprint("runs", __name__)

@runs_bp.post("")
def create_run():
    s = current_app.config["SETTINGS"]
    db = current_app.config["DB"]
    body = request.get_json(force=True)
    run_id = db.insert_run(
        org_id=body["org_id"],
        location_id=body["location_id"],
        run_date=body["run_date"]
    )
    return {"id": run_id}, 201

@runs_bp.get("/<run_id>")
def read_run(run_id):
    db = current_app.config["DB"]
    data = db.get_run(run_id)
    if not data: return {"error": "not found"}, 404
    return data