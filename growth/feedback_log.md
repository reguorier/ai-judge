# AI Judge Citation Audit Feedback Log

This file records public launch links, replies, objections, and product signals from the 30-day growth plan.

## Launch Links

| Date | Channel | URL | Status | Notes |
|---|---|---|---|---|
| 2026-05-17 | Hugging Face Community | https://huggingface.co/spaces/reguorier/ai-judge-citation-audit/discussions/new | blocked_by_rate_limit | Draft prepared in `growth/huggingface_community_post.md`; page says the account is rate-limited and can retry later. |
| 2026-05-17 | Hacker News | https://news.ycombinator.com/submit | blocked_by_browser | Draft prepared in `growth/show_hn_launch_post.md`; in-app browser reports `net::ERR_BLOCKED_BY_CLIENT`. |
| 2026-05-17 | X | https://x.com/liuweidi2/status/2055973517779521750 | live | First short-form launch post published from logged-in Chrome. |
| 2026-05-17 | Zhihu | https://zhuanlan.zhihu.com/p/2039446444000665819 | live | Chinese long-form launch article published successfully from logged-in Chrome. |
| 2026-05-17 | Reddit r/LocalLLaMA | https://www.reddit.com/r/LocalLLaMA/comments/1tfohfv/ | posted_then_removed_by_moderation | Logged in as `u/ExpensiveHunt2055`, posted with `Resources` flair, then r/LocalLLaMA moderation removed it from the subreddit feed. |
| 2026-05-17 | Hacker News | https://news.ycombinator.com/showlim | blocked_platform_show_hn_restriction | Logged-in submit flow reached the current HN Show HN restriction page for newer/unfamiliar users. |
| 2026-05-17 | V2EX | https://www.v2ex.com/invite/activate | blocked_account_activation_required | Logged in as `reguorider`, but the account cannot post until an invite code or `$V2EX` activation is completed. |
| 2026-05-18 | Hugging Face Community | https://huggingface.co/spaces/reguorier/ai-judge-citation-audit/discussions/new | blocked_by_hcaptcha | HF login and email confirmation are complete, but the public discussion submit flow is blocked by repeated hCaptcha challenges. Draft remains in `growth/huggingface_community_post.md`. |
| 2026-05-18 | V2EX | https://www.v2ex.com/invite/activate | abandoned_activation_unavailable | User confirmed no activation code is available; stop spending automation time on V2EX until activation exists. |
| 2026-05-17 | Hacker News | https://news.ycombinator.com/submit | blocked_by_login | Chrome reaches submit page, but HN account is not logged in. |
| 2026-05-17 | Reddit | https://www.reddit.com/r/LocalLLaMA/submit | blocked_by_login | Chrome is not logged into Reddit. |
| 2026-05-17 | Hugging Face Community | https://huggingface.co/spaces/reguorier/ai-judge-citation-audit/discussions/new | blocked_by_login | Chrome is not logged into Hugging Face. |
| 2026-05-17 | V2EX | https://www.v2ex.com/new | blocked_by_login | Chrome is not logged into V2EX. |
| 2026-05-17 | Zhihu | https://www.zhihu.com/question/waiting | blocked_by_login | Chrome is not logged into Zhihu. |

## Signals

| Date | Source | Signal | Action |
|---|---|---|---|
| 2026-05-17 | Space verification | Default citation audit runs online and returns Certification ID + Replay Ledger. | Use Space as the primary demo link. |
| 2026-05-17 | Hugging Face Community | New discussion form is disabled by platform rate limit. | Retry after account limit lifts; do not spend more time on HF posting today. |
| 2026-05-17 | Hacker News | Submit page blocked by current in-app browser. | Use regular browser manually or retry from a different browser session before launch confirmation. |
| 2026-05-17 | GitHub issues | Issue queue prepared. | Create labels and issues after final confirmation; source file is `growth/github_issue_queue.md`. |
| 2026-05-17 | GitHub issues | Created labels and issues #2-#5 for benchmark cases, label boundary feedback, batch audit demand, and demo gallery examples. | Use these links as the primary low-friction contribution funnel in public posts. |
| 2026-05-17 | GitHub release | Updated v3.6.0 release notes with hard benchmark and public contribution funnel. | Release page now sends visitors to issues #2-#5. |
| 2026-05-17 | X launch | Published short-form post. A first malformed attempt was deleted immediately; clean intent/post version is live. | Watch for replies and profile visits. |
| 2026-05-17 | Zhihu launch | Published the Chinese long-form article at https://zhuanlan.zhihu.com/p/2039446444000665819. | Track reads, comments, and whether Chinese users understand `unverifiable` as a non-false label. |
| 2026-05-17 | Reddit launch | r/LocalLLaMA accepted the post initially, then removed it by moderation. | Do not repost the same text; next Reddit action should be a lower-promotion, benchmark-case discussion or a reply where directly relevant. |
| 2026-05-17 | Hacker News | HN blocks Show HN for the current account context with `showlim`. | Do not retry repeatedly; build HN account context or wait until the platform restriction lifts. |
| 2026-05-17 | V2EX | Account is logged in but unactivated. | Post only after invite-code or `$V2EX` activation. |
| 2026-05-18 | Hugging Face Community | HF account is logged in and email-confirmed, but repeated hCaptcha challenges block discussion creation. | Treat as platform friction, not product failure; avoid repeated CAPTCHA retries and use Space/GitHub/X/Zhihu links as active launch surfaces. |
| 2026-05-18 | V2EX | Activation code is unavailable. | Mark V2EX abandoned for this launch cycle. |
| 2026-05-17 | GitHub metadata | Attempted to update repo description, homepage, and topics. | Blocked by GitHub API 404 from current `gh repo edit` permission path; push/issue/release permissions still work. |
| 2026-05-17 | GitHub issue #1 | https://github.com/reguorier/ai-judge/issues/1#issuecomment-4470493105 | Added comment linking issue #1 to the new launch contribution funnel. |
| 2026-05-17 | Demo gallery | Added `legal-memo-contradicted` and `opensource-readme-irrelevant` demos with generated HTML/JSON reports. | This satisfies the first concrete acceptance step for issue #5 while keeping the issue open for more community examples. |
| 2026-05-17 | GitHub issue #5 | https://github.com/reguorier/ai-judge/issues/5#issuecomment-4470644643 | Posted progress update linking the two new demo reports back to the public issue. |
| 2026-05-17 | Blog draft | `docs/AI_COLLECTIVE_BLIND_SPOTS_BLOG.md` | Expanded the "9 AI collective blind spots" outline into a publish-ready long-form essay. |

## Public Contribution Links

| Topic | URL |
|---|---|
| Hard citation hallucination cases | https://github.com/reguorier/ai-judge/issues/2 |
| `unverifiable` vs `contradicted` edge cases | https://github.com/reguorier/ai-judge/issues/3 |
| Batch Markdown/PDF/Docx demand | https://github.com/reguorier/ai-judge/issues/4 |
| Demo gallery examples | https://github.com/reguorier/ai-judge/issues/5 |
| X launch post | https://x.com/liuweidi2/status/2055973517779521750 |
| Zhihu long-form launch | https://zhuanlan.zhihu.com/p/2039446444000665819 |
| Reddit r/LocalLLaMA launch attempt | https://www.reddit.com/r/LocalLLaMA/comments/1tfohfv/ |

## Objections To Track

| Objection | Current answer | Follow-up needed |
|---|---|---|
| How is this different from RAG eval tools? | Narrow citation-level source isolation before publishing. | Add competitor comparison section if repeated. |
| Why is `unverifiable` not `false`? | Missing evidence is not contradiction. | Turn into Day 28 explainer. |
| Can it audit PDF/Docx/batches? | Planned Pro scope. | Convert repeated asks into paid feature validation. |
