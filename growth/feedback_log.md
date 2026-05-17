# AI Judge Citation Audit Feedback Log

This file records public launch links, replies, objections, and product signals from the 30-day growth plan.

## Launch Links

| Date | Channel | URL | Status | Notes |
|---|---|---|---|---|
| 2026-05-17 | Hugging Face Community | https://huggingface.co/spaces/reguorier/ai-judge-citation-audit/discussions/new | blocked_by_rate_limit | Draft prepared in `growth/huggingface_community_post.md`; page says the account is rate-limited and can retry later. |
| 2026-05-17 | Hacker News | https://news.ycombinator.com/submit | blocked_by_browser | Draft prepared in `growth/show_hn_launch_post.md`; in-app browser reports `net::ERR_BLOCKED_BY_CLIENT`. |

## Signals

| Date | Source | Signal | Action |
|---|---|---|---|
| 2026-05-17 | Space verification | Default citation audit runs online and returns Certification ID + Replay Ledger. | Use Space as the primary demo link. |
| 2026-05-17 | Hugging Face Community | New discussion form is disabled by platform rate limit. | Retry after account limit lifts; do not spend more time on HF posting today. |
| 2026-05-17 | Hacker News | Submit page blocked by current in-app browser. | Use regular browser manually or retry from a different browser session before launch confirmation. |
| 2026-05-17 | GitHub issues | Issue queue prepared. | Create labels and issues after final confirmation; source file is `growth/github_issue_queue.md`. |

## Objections To Track

| Objection | Current answer | Follow-up needed |
|---|---|---|
| How is this different from RAG eval tools? | Narrow citation-level source isolation before publishing. | Add competitor comparison section if repeated. |
| Why is `unverifiable` not `false`? | Missing evidence is not contradiction. | Turn into Day 28 explainer. |
| Can it audit PDF/Docx/batches? | Planned Pro scope. | Convert repeated asks into paid feature validation. |
