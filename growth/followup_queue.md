# Follow-Up Queue

Status: ready for use after first replies

## Platform Recovery Queue

| Channel | Current state | Next automatic action |
|---|---|---|
| Hugging Face Community | Login/email confirmation complete, but hCaptcha blocks public discussion creation. | Do not retry repeatedly; use Space/GitHub/X/Zhihu as active links and retry HF only after a cooldown or manual CAPTCHA completion. |
| Hacker News | `showlim` blocks Show HN for this account context. | Do not retry immediately; return only after the account has normal community activity or the restriction lifts. |
| Reddit r/LocalLLaMA | Launch post was removed by moderation. | Do not repost the same text; use replies to directly relevant citation-hallucination threads or ask moderators before a second post. |
| V2EX | Logged in, but activation code is unavailable. | Abandon V2EX for this launch cycle; resume only if an invite code or `$V2EX` activation appears. |
| Zhihu | Article published. | Track comments and route useful examples into benchmark issues #2-#5. |
| Direct email | QQ Mail is logged in through Safari; Apple Mail accounts fail IMAP/SMTP login; Chrome automation is blocked because the Codex Chrome extension is disabled. | Use `growth/outreach_mailto_links.md` or `growth/outreach_drafts/*.eml` for the first P0 send batch; record sent status immediately after sending. |

## Follow-up 1: benchmark contributor

```text
Thanks for the example. I can add an anonymized version to the citation benchmark if you are comfortable with that.

The fields I need are:
- AI answer text or summary
- cited source
- isolated evidence, if available
- expected label
- why the label fits
```

## Follow-up 1A: P0 governance reply

Status: draft only, send only after action-time confirmation.

```text
Hi,

This is exactly the kind of reply I was hoping for. Thank you for taking the tool seriously enough to run the taxonomy against a hard case instead of just reacting to the pitch.

I agree with the main critique: citation-level labels are a useful MVP, but legal/audit use needs the smaller atom of claim-span plus source. Your benchmark direction is valuable because it forces the label boundary between source relevance and claim support instead of letting "real source" accidentally become "verified claim."

I am going to treat your note as five concrete work items:

1. Add an anonymized fixture for the label-boundary case after permission.
2. Split `unverifiable` reason codes so fabricated source and inaccessible source are not collapsed.
3. Separate evidence provenance classes: user_supplied, fetched, independently_attested, and notarized.
4. Add a claim-span/source roadmap note for legal and audit workflows.
5. Tighten the license wording so I do not casually call BSL "open-source" when the trust posture needs more precision.

I would like to take you up on the offer to run one AI Judge audit case through your governance framing. The cleanest first case is the fabricated-source demo because it exercises the exact "do not write hallucinated evidence into a ledger" boundary. If you prefer, I can send the raw answer, isolated evidence JSON, and audit result as three separate blocks so the test preserves source isolation end to end.

Best,
Reguorier
```

## Follow-up 2: Pro interest

```text
That sounds like the Pro workflow I am validating.

Which input do you need next: stricter Markdown/JSON batch CI, PDF, Docx, or GitHub PR comments?

I am keeping the first paid version narrow: executable Markdown/JSON batch audit, Evidence Broker network mode, historical Replay Ledger, and exportable Certification reports. PDF/Docx are now visible as pending-parser inputs instead of being silently skipped.
```

## Follow-up 3: free audit

```text
I can run one anonymized AI-generated answer or memo through the audit and send back the HTML/JSON report.

No private data will be published without permission. The audit preserves the raw answer and does not rewrite it.
```
