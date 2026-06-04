"""Submit AI Judge client runs via local API or direct local orchestrator."""

from __future__ import annotations

import json
import urllib.request
from typing import Any

from product.run_orchestrator import create_client_run


def submit_direct(question: str, mode: str = "deep_judge", auto_complete: bool = True) -> dict[str, Any]:
    return create_client_run(question=question, mode=mode, auto_complete=auto_complete)


def submit_api(api_base: str, question: str, mode: str = "deep_judge", auto_complete: bool = True) -> dict[str, Any]:
    payload = json.dumps({"question": question, "mode": mode, "auto_complete": auto_complete}).encode("utf-8")
    request = urllib.request.Request(
        api_base.rstrip("/") + "/api/client/runs",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))
