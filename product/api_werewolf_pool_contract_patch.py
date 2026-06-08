
# === PATCH: Werewolf + Pool contract endpoints ===

@app.route("/api/werewolf/<game_id>/contract", methods=["GET"])
def werewolf_contract(game_id: str):
    """Generate AJ_REPORT_V1 contract from werewolf game result."""
    session = get_werewolf_session(game_id)
    if not session:
        return jsonify({"error": "werewolf session not found"}), 404
    try:
        from core.verdict_to_contract_bridge import verdict_to_report_contract
        verdict = {
            "mode": "werewolf",
            "run_id": game_id,
            "werewolf_session": session,
            "winning_team": session.get("winning_team", "unknown"),
            "question": "狼人杀对局",
        }
        contract = verdict_to_report_contract(verdict)
        return jsonify(contract)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/werewolf/<game_id>/decision-brief", methods=["GET"])
def werewolf_decision_brief(game_id: str):
    """Render werewolf game as AJ_REPORT_V1 HTML."""
    session = get_werewolf_session(game_id)
    if not session:
        return jsonify({"error": "werewolf session not found"}), 404
    try:
        from core.verdict_to_contract_bridge import verdict_to_report_contract
        verdict = {
            "mode": "werewolf",
            "run_id": game_id,
            "werewolf_session": session,
            "winning_team": session.get("winning_team", "unknown"),
            "question": "狼人杀对局",
        }
        contract = verdict_to_report_contract(verdict)
        return jsonify({"contract": contract, "mode": "werewolf"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/worldcup-pool/<round_id>/contract", methods=["GET"])
def pool_contract(round_id: str):
    """Generate AJ_REPORT_V1 contract from prediction pool round."""
    try:
        from core.verdict_to_contract_bridge import verdict_to_report_contract
        verdict = {
            "mode": "worldcup_pool",
            "run_id": round_id,
            "worldcup_pool": {"round_id": round_id},
            "question": "预测池",
        }
        contract = verdict_to_report_contract(verdict)
        return jsonify(contract)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/worldcup-pool/<round_id>/decision-brief", methods=["GET"])
def pool_decision_brief(round_id: str):
    """Render prediction pool round as AJ_REPORT_V1 HTML."""
    try:
        from core.verdict_to_contract_bridge import verdict_to_report_contract
        verdict = {
            "mode": "worldcup_pool",
            "run_id": round_id,
            "worldcup_pool": {"round_id": round_id},
            "question": "预测池",
        }
        contract = verdict_to_report_contract(verdict)
        return jsonify({"contract": contract, "mode": "prediction_pool"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
