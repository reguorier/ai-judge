# Submission Fit-Check Queue

Status: active, partially blocked by mail deliverability
Last checked: 2026-05-20 16:42 HKT

This queue holds venue-specific fit-check drafts created from the submission
council. These are external actions and must not be sent without action-time
confirmation.

## Current Mailbox Check

- QQ Mail was checked in Safari at 2026-05-19 05:28 HKT.
- No new Eval4SD organizer reply or OpenReview backup-route instruction was
  visible in the inbox.
- Visible new OpenReview messages were profile activation/moderation notices,
  not a submission-route resolution.
- RLEval fit-check was sent from `liuweidi@flywise.cn` at 2026-05-20 06:32 HKT
  after user confirmation, but immediately bounced from Google Groups because
  the `flywise.cn` sender domain failed SPF/DKIM authentication.
- CLEAR fit-check was sent from Tencent Enterprise Mail after the user later
  confirmed continuing the external automation batch.

## Prepared Drafts

| ID | Target | Route | Draft | Status | Gate |
|---|---|---|---|---|---|
| W005 | RLEval 2026 | `rl-eval@googlegroups.com` | `growth/email_drafts/w005_rleval_fit_check.eml` | bounced_spf_dkim | find authenticated sender or alternate route |
| W006 | CLEAR 2026 | `themis.xanthopoulou@umu.se` | `growth/email_drafts/w006_clear_fit_check.eml` | sent | monitor for reply |

## Deliverability Blocker

Google Groups rejected the RLEval message with:

`550-5.7.26 Your email has been blocked because the sender is unauthenticated. Gmail requires all senders to authenticate with either SPF or DKIM.`

Observed failure:

- DKIM did not pass.
- SPF for `flywise.cn` did not pass from Tencent Exmail outbound IP.

Recommended recovery:

1. Fix `flywise.cn` DNS authentication for Tencent Enterprise Mail:
   - Add/repair the Tencent Exmail SPF TXT record.
   - Enable and publish DKIM for the domain from the enterprise mail admin panel.
   - If DMARC exists, keep it permissive until SPF/DKIM alignment is verified.
2. Resend RLEval only after DNS propagation, or send from an already
   authenticated personal Gmail / institutional address with the same content.
3. If the RLEval deadline is still active, use OpenReview or a verified
   organizer alternate contact instead of retrying the rejected Google Group.

## Why These Are Next

- Both routes are close-window research credibility paths.
- Neither requires publishing private correspondence.
- Both reuse the same source-isolated claim-support wedge already implemented
  in the Eval4SD packet, hard benchmark, and proof kit.

## Send Guardrail

The remaining drafts are prepared so confirmation can be fast. Sending new
email, uploading attachments, or final-submitting to OpenReview remains a
separate external action.
