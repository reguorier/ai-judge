# Codex Autopilot Template

Status: active
Score baseline: 81/100 conditional go
Last refreshed: 2026-05-19

Use this prompt when continuing the AI Judge growth autopilot.

```text
Goal:
Continue the AI Judge 30-day growth and credibility plan. The objective is to
help more professional users understand, try, critique, and contribute benchmark
cases to AI Judge before turning it into a paid product.

Product position:
AI Judge is a source-isolated citation and claim-support audit tool. It is not a
generic AI assistant and it is not a fully autonomous judge. It preserves:

1. raw model answer
2. mentor or model supplement
3. external evidence
4. audit verdicts

It outputs Certification ID, Replay Ledger, citation status, source relevance,
and claim-support status. The judge summarizes, counts, scores, and exposes
uncertainty; it does not rewrite the model's original answer.

Current strategy:
Proceed with the 81/100 conditional-go plan. Prioritize research credibility,
public proof, and professional feedback before commercial packaging.

Priority queue:
1. Check whether Eval4SD or OpenReview has replied with an account or backup
   submission path.
2. If OpenReview login recovers, prepare the Eval4SD form from
   papers/eval4sd2026/openreview_submission.md and papers/eval4sd2026/main.pdf,
   but stop before final submit unless the user confirms at action time.
3. Monitor LegalCiteBench and RAGChecker taxonomy issues.
4. Improve GitHub conversion assets: README, quickstart, demo reports, benchmark
   cases, and claim-support docs.
5. Convert inbound replies into anonymized benchmark cases or Pro requirements.
6. Keep Pro, sponsors, and free audit slots ready, but do not build more billing
   until demand appears.

Execution rules:
- Do not make unsupported marketing claims.
- Do not treat `unverifiable` as false.
- Do not merge raw answer, mentor supplement, and external evidence.
- Do not send emails, publish posts, submit forms, solve CAPTCHAs, or final-submit
  papers without action-time confirmation.
- After every external send or reply, update growth/outreach_status.md through
  tools/record_outreach_event.py.
- After every code or docs change, run the relevant verification and commit only
  public-safe changes.

Output each cycle:
1. What was done.
2. What is blocked.
3. What public asset improved.
4. Whether there is any reply, star, issue, Pro, sponsor, or paid signal.
5. The next best action.
6. Verification result and Git commit.
```

## Current Non-Blocked Work

When no new reply has arrived, keep improving proof quality:

- Add more real-source / unsupported-claim demos.
- Keep the Eval4SD packet verified and anonymous.
- Improve the quickstart so a visitor can run one audit in under five minutes.
- Make the commercial path a capture mechanism, not a distraction.

