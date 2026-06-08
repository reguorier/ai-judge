
# === PATCH: Report contract endpoint ===
# Add this to api_server.py routes

@app.route("/api/runs/<run_id>/contract", methods=["GET"])
def get_run_contract(run_id: str):
    """Return the AJ_REPORT_V1_DECISION_BRIEF contract for a run."""
    result = get_run(run_id)
    if not result:
        return jsonify({"error": "run not found"}), 404
    try:
        from core.verdict_to_contract_bridge import verdict_to_report_contract
        contract = verdict_to_report_contract(result)
        return jsonify(contract)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/runs/<run_id>/decision-brief", methods=["GET"])
def get_run_decision_brief(run_id: str):
    """Render and return the decision brief HTML for a run."""
    result = get_run(run_id)
    if not result:
        return jsonify({"error": "run not found"}), 404
    try:
        from core.verdict_to_contract_bridge import verdict_to_report_contract
        contract = verdict_to_report_contract(result)
        # In production, this would call the TypeScript renderer via subprocess
        # For now, return the contract JSON
        return jsonify({"contract": contract, "note": "Pass this to renderDecisionBriefReport()"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
