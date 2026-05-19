# Email Deliverability Fix - 2026-05-20

Status: required before retrying Google Groups targets from `liuweidi@flywise.cn`

## Trigger

The RLEval fit-check to `rl-eval@googlegroups.com` was accepted by Tencent
Enterprise Mail as sent, then immediately bounced by Google Groups.

The rejection says Gmail blocked the sender because `flywise.cn` is
unauthenticated:

- DKIM: did not pass
- SPF: did not pass

## Why This Matters

This affects any Google/Gmail/Google Groups recipient. Repeating the same send
from `liuweidi@flywise.cn` will likely bounce again until the domain publishes
valid mail authentication records.

## Fix Checklist

1. In Tencent Enterprise Mail admin, locate domain DNS setup for `flywise.cn`.
2. Publish the recommended SPF TXT record for Tencent Exmail outbound mail.
3. Enable DKIM signing for `flywise.cn` and publish the DKIM TXT/CNAME record
   exactly as Tencent provides it.
4. If a DMARC TXT record exists, keep policy at `p=none` or permissive while
   verifying SPF/DKIM alignment.
5. Wait for DNS propagation, then send a test message to a Gmail address.
6. Retry Google Groups only after the test message shows SPF or DKIM pass.

## Operational Workaround

For time-sensitive workshop fit-checks:

- Use an already authenticated Gmail, university, or institutional mailbox.
- Or use OpenReview / website contact forms where available.
- Do not retry Google Groups from `flywise.cn` until DNS authentication passes.
