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
| 2026-05-18 | LegalCiteBench GitHub Issue | https://github.com/Sijia711/LegalCiteBench/issues/1 | live | Posted public taxonomy exchange because arXiv/GitHub/HF dataset expose no public email. |
| 2026-05-18 | RAGChecker GitHub Issue | https://github.com/amazon-science/RAGChecker/issues/38 | live | RefChecker route was archived/read-only, so the claim-span/source question was reframed as RAG faithfulness and posted to active RAGChecker. |
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
| 2026-05-18 | Direct outreach | First real outreach batch prepared in `growth/outreach_batch_001.md` with legal AI, LLM eval, hallucination tooling, and research targets. | Send low-volume personalized messages from the available mailbox/channel and log replies. |
| 2026-05-18 | Direct outreach send path | Generated P0 mailto links and `.eml` drafts in `growth/outreach_mailto_links.md` and `growth/outreach_drafts/`; Apple Mail is not send-capable, QQ Mail is logged in via Safari, Chrome extension is disabled. | Use QQ Mail or enable the Chrome extension before browser-driven sends; update send log after each message. |
| 2026-05-18 | Direct outreach tracking | Added `tools/record_outreach_event.py`, `growth/outreach_events.jsonl`, and generated `growth/outreach_status.md` so sent/reply/bounce/pro-signal events can be logged with one command. | Use the logger immediately after each send or reply. |
| 2026-05-18 | Free audit funnel | Added three-slot tracker and intake message for free AI Decision Audits in exchange for testimonial or public-safe lesson permission. | Reserve a slot when a reply expresses interest. |
| 2026-05-18 | Pro early access | Added Pro interest event tracking and upgraded the early-access CTA to collect workflow, volume, and use-case fields. | Record inbound Pro requests with `tools/record_pro_interest.py`. |
| 2026-05-18 | Sponsors | Added manual sponsor intake and event tracking while GitHub Sponsors remains disabled. | Record sponsor requests or manual support with `tools/record_sponsor_event.py`. |
| 2026-05-18 | Private outreach handling | Private replies and permission-pending benchmark leads are intentionally not recorded in the public repo with target-level details. | Keep private notes outside the repo, ask before replying, and only convert material into public benchmark fixtures after anonymization or explicit permission. |
| 2026-05-18 | Anonymized benchmark feedback | A private governance/audit reply highlighted the "real source shows correlation, model claims causation" boundary. | Added an anonymized hard benchmark case and claim-span/source roadmap without publishing private correspondence. |
| 2026-05-18 | Steve Sonza / Article 11 product sync | The core issue was "real source only supports relevance/association, but the model claims causation." | Added a public-safe local demo input/report for real-source overclaimed causation, keeping private correspondence out of GitHub. |
| 2026-05-18 | GitHub issue #5 | https://github.com/reguorier/ai-judge/issues/5#issuecomment-4477178697 | Posted the real-source overclaimed-causation demo to the public demo gallery issue. |
| 2026-05-18 | GitHub issue #3 | https://github.com/reguorier/ai-judge/issues/3#issuecomment-4477215299 | Added the real-source/unsupported-conclusion boundary to the `unverifiable` vs `contradicted` discussion. |
| 2026-05-18 | Hugging Face Space source | `spaces/citation-audit/app.py` | Added a built-in sample switcher and claim-support summary so the Space can demonstrate both fabricated citations and real-source/unsupported-claim audits. |
| 2026-05-18 | Hugging Face Space deploy | https://huggingface.co/spaces/reguorier/ai-judge-citation-audit | Space Git remote is readable and was cloned, but push failed with `Invalid username or password`; deployment now needs an HF write token or browser upload flow. |
| 2026-05-18 | Hugging Face deploy helper | `tools/deploy_hf_space.py` | Added a repeatable Space deployment helper; default mode prepares/validates, `--push` requires `HF_TOKEN`. |
| 2026-05-18 | Trust wording | BSL 1.1 wording can undermine governance positioning if described casually as open source. | README and launch docs now use source-available wording where appropriate. |
| 2026-05-18 | Article 11 reply | Sent a public-safe reply through QQ Mail with the f22f2de update, claim-span roadmap, and Truth Gate demo invitation. | Wait for their Truth Gate response before sending raw/evidence/audit blocks. |
| 2026-05-18 | Resonance Wave 002 | Prepared a targeted queue for Eval4SD, LegalCiteBench, HalluCiteChecker, LLMTrust, Aequis, Ligate, AEX, audit-trail research, GEM, FAGEN, and public legal/RAG discussions. | Use `growth/resonance_wave_002.md`; each external send still needs action-time confirmation. |
| 2026-05-18 | Eval4SD paper packet | `papers/eval4sd2026/main.tex` | Created an anonymous 4-page short/position-paper source with benchmark tables, overclaimed-causation row, bibliography, README, and submission checklist. |
| 2026-05-18 | Eval4SD paper gate | `tools/check_eval4sd_packet.py` | Added a pre-submit script that checks paper anonymity, bibliography keys, and benchmark table values against current deterministic benchmark output. |
| 2026-05-18 | Eval4SD organizer reply | QQ Mail / eval4sd-organizers | Organizer confirmed the source-isolated citation audit topic is a strong workshop fit; short/position paper is appropriate, and demo paper with limited evaluation would also work. Thank-you reply sent via QQ Mail. |
| 2026-05-18 | Eval4SD ACL template | `papers/eval4sd2026/acl.sty` | Added official ACL style files and switched the anonymous draft to `\usepackage[review]{acl}`. |
| 2026-05-18 | Eval4SD PDF build | `papers/eval4sd2026/main.pdf` | Installed Tectonic, built a 3-page anonymous ACL review PDF, and confirmed extracted text has no obvious identity leaks. |
| 2026-05-18 | LegalCiteBench taxonomy route | No public email was exposed by the arXiv PDF, GitHub repository, or Hugging Face dataset card, but Issues were enabled. | Posted `https://github.com/Sijia711/LegalCiteBench/issues/1`; monitor for replies before adding benchmark mapping claims. |
| 2026-05-18 | Aequis route investigation | Site direction matches legal AI provenance benchmarks, but contact links are Cloudflare-protected and local DNS/TLS fails; no verified email or GitHub org route found. | Keep as blocked; retry only from a clean DNS/network path or verified public channel, not guessed email. |
| 2026-05-18 | RAGChecker taxonomy route | RefChecker is archived/read-only; RAGChecker is active, not archived, and has Issues enabled. | Posted `https://github.com/amazon-science/RAGChecker/issues/38`; monitor for taxonomy feedback. |
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
| LegalCiteBench taxonomy exchange | https://github.com/Sijia711/LegalCiteBench/issues/1 |
| RAGChecker taxonomy exchange | https://github.com/amazon-science/RAGChecker/issues/38 |
| X launch post | https://x.com/liuweidi2/status/2055973517779521750 |
| Zhihu long-form launch | https://zhuanlan.zhihu.com/p/2039446444000665819 |
| Reddit r/LocalLLaMA launch attempt | https://www.reddit.com/r/LocalLLaMA/comments/1tfohfv/ |

## Objections To Track

| Objection | Current answer | Follow-up needed |
|---|---|---|
| How is this different from RAG eval tools? | Narrow citation-level source isolation before publishing. | Add competitor comparison section if repeated. |
| Why is `unverifiable` not `false`? | Missing evidence is not contradiction. | Turn into Day 28 explainer. |
| Can it audit PDF/Docx/batches? | Planned Pro scope. | Convert repeated asks into paid feature validation. |
| Does citation-level verdict hide mixed legal or audit claims? | Yes. Citation-level audit is the MVP; legal/audit use needs `claim-span + source`. | Added `docs/CLAIM_SPAN_ROADMAP.md`; next implementation should extract claim spans before scoring source support. |
| Is user-supplied evidence equivalent to fetched or attested evidence? | No. Source isolation is necessary but not sufficient for provenance. | Added evidence provenance classes: `model_candidate`, `user_supplied`, `fetched`, `independently_attested`, `notarized`. |
| Is BSL compatible with trust infrastructure positioning? | It can be, but the product must say source-available under BSL 1.1, not OSI open source. | Continue replacing old launch drafts before reuse; sent outreach records remain historical. |
