# External Action Queue

Prepared and partially executed. Each remaining action needs user confirmation because it posts, submits, emails, or DMs externally.

| Priority | Action | Destination | Prepared Asset | Confirmation Needed |
|---|---|---|---|---|
| P0 | Submit MiraclePlus application | https://www.miracleplus.com/apply/ | `miracleplus_application_pack_2026-05-20.md` | Completed |
| P0 | Post Show HN | https://news.ycombinator.com/showhn.html | `github_star_sprint_7_30_2026-05-20.md` | Yes |
| P0 | Post Reddit LocalLLaMA | Reddit | `github_star_sprint_7_30_2026-05-20.md` | Yes |
| P0 | Post X thread | X account | `github_star_sprint_7_30_2026-05-20.md` | Yes |
| P1 | DM / email 20 targets | Mixed channels | `outreach_targets_20_2026-05-20.csv` | Yes |
| P1 | Product Hunt prep / launch | https://www.producthunt.com/launch | `github_star_sprint_7_30_2026-05-20.md` | Yes |
| P1 | CLEAR fit-check email | `themis.xanthopoulou@umu.se` | `growth/email_drafts/w006_clear_fit_check.eml` | Yes, currently composed not sent |
| P1 | RLEval fit-check retry | `rl-eval@googlegroups.com` or alternate route | `growth/email_drafts/w005_rleval_fit_check.eml` | Only after SPF/DKIM fix or authenticated alternate sender |

## Fast Approval Script For User

If you want me to proceed with a specific external action, say one of:

- "确认提交奇绩申请"
- "确认发布 Show HN"
- "确认发布 Reddit"
- "确认发送 20 人触达"
- "确认准备 Product Hunt"
- "确认发送 CLEAR 邮件"

I will then operate the UI and stop at any credential, payment, upload, or final confirmation boundary if the page requires a new sensitive step.
