# Eval4SD Fastlane Status

Generated: `2026-05-18T22:56:45.104386+00:00`

Ready for form fill: **True**

This receipt does not submit the paper, send emails, publish posts, or solve CAPTCHA.

| Step | Status | Command | Detail |
|---|---|---|---|
| packet | PASS | `/opt/homebrew/opt/python@3.14/bin/python3.14 tools/check_eval4sd_packet.py` | anonymous=True; full=100/100; hard=13/13 |
| bench-100 | PASS | `/opt/homebrew/opt/python@3.14/bin/python3.14 tools/run_citation_bench.py --fail-under 0.95` | 100/100 passed, accuracy 1.0 |
| hard-13 | PASS | `/opt/homebrew/opt/python@3.14/bin/python3.14 tools/run_citation_bench.py --bench citation-bench/citation-bench-hard-11.jsonl --fail-under 0.95` | 13/13 passed, accuracy 1.0 |

## Submission Assets

- Paper source: `papers/eval4sd2026/main.tex`
- PDF: `papers/eval4sd2026/main.pdf`
- OpenReview packet: `papers/eval4sd2026/openreview_submission.json`

## Manual Gate

OpenReview account access or organizer backup route; final submission still requires action-time confirmation.
