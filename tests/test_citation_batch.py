from pathlib import Path

from core.citation_batch import expand_batch_inputs, run_audit_batch


def _write_verified_case(path: Path) -> None:
    path.write_text(
        """# Verified Batch Case

## Question
Does the answer cite the AI Judge citation audit report?

## AI Answer
AI Judge includes citation audit support. Source: https://example.com/ai-judge-citation-audit

## External Evidence
```json
[
  {
    "id": "EVID-001",
    "url": "https://example.com/ai-judge-citation-audit",
    "title": "AI Judge citation audit report",
    "snippet": "citation audit support for AI Judge launch",
    "text": "AI Judge includes citation audit support for launch workflows.",
    "status": "user_supplied"
  }
]
```
""",
        encoding="utf-8",
    )


def _write_unverifiable_case(path: Path) -> None:
    path.write_text(
        """# Unverifiable Batch Case

## Question
Does the answer prove a made-up citation?

## AI Answer
The 2026 Example Citation Index says citation errors are solved. Source: https://example.invalid/citation-index-2026
""",
        encoding="utf-8",
    )


def test_expand_batch_inputs_accepts_directory_and_supported_files(tmp_path: Path):
    _write_verified_case(tmp_path / "one.md")
    (tmp_path / "ignore.txt").write_text("nope", encoding="utf-8")

    paths = expand_batch_inputs([tmp_path])

    assert [path.name for path in paths] == ["one.md"]


def test_run_audit_batch_writes_manifest_and_index(tmp_path: Path):
    input_dir = tmp_path / "inputs"
    input_dir.mkdir()
    _write_verified_case(input_dir / "verified.md")
    _write_unverifiable_case(input_dir / "unverifiable.md")
    out_dir = tmp_path / "batch"

    manifest = run_audit_batch(
        [input_dir],
        out_dir=out_dir,
        batch_id="batch-test",
        fail_on=["contradicted"],
        warn_on=["unverifiable"],
        generated_at="2026-05-18T00:00:00+00:00",
    )

    assert manifest["schema"] == "citation_audit_batch.v1"
    assert manifest["input_count"] == 2
    assert manifest["failed_count"] == 0
    assert manifest["warning_count"] >= 1
    assert manifest["exit_code"] == 0
    assert (out_dir / "manifest.json").exists()
    assert (out_dir / "index.html").exists()
    assert all(Path(item["html"]).exists() for item in manifest["results"])
    assert all(Path(item["json"]).exists() for item in manifest["results"])


def test_run_audit_batch_can_fail_on_policy_status(tmp_path: Path):
    input_dir = tmp_path / "inputs"
    input_dir.mkdir()
    _write_unverifiable_case(input_dir / "unverifiable.md")

    manifest = run_audit_batch(
        [input_dir],
        out_dir=tmp_path / "batch",
        batch_id="batch-fail-test",
        fail_on=["unverifiable"],
        warn_on=[],
        generated_at="2026-05-18T00:00:00+00:00",
    )

    assert manifest["failed_count"] == 1
    assert manifest["warning_count"] == 0
    assert manifest["exit_code"] == 1
