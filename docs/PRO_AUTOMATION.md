# Citation Audit Pro Automation

This is the automation path for the first self-serve revenue loop. It avoids manual consulting and keeps the purchase flow simple.

## Product

| Tier | Price | Automation |
|---|---:|---|
| Free | $0 | Single Markdown/JSON audit, local HTML/JSON report, 100-case benchmark |
| Pro Early Bird | $49 lifetime | Batch audit, Evidence Broker network fetch, history ledger, GitHub Action advanced mode |
| Pro Monthly | $19/month | Same as Pro, subscription license |
| Pro Lifetime | $199 lifetime | Same as Pro, lifetime license |

## Checkout setup

Preferred first provider: Lemon Squeezy.

Products to create:

1. `AI Judge Citation Audit Pro Early Bird` - $49 lifetime, first 100 users.
2. `AI Judge Citation Audit Pro Monthly` - $19/month.
3. `AI Judge Citation Audit Pro Lifetime` - $199 lifetime.

Required checkout fields:

- buyer email
- GitHub username, optional
- intended use: Markdown, PDF, Docx, GitHub PRs, or other

## License delivery

MVP path:

1. Lemon Squeezy generates license keys.
2. Buyer receives the license key in the purchase email.
3. User runs:

```bash
ai-judge license activate --key AJPRO-...
```

4. Pro features check license status before batch/network/history actions.

## Automation owner

Codex can run the setup flow after the user logs in:

1. Open Lemon Squeezy.
2. Create the three products.
3. Copy checkout URLs into `product/checkout_config.json`.
4. Update README and landing page CTA links.
5. Run a test purchase only if the user explicitly approves spending money.

## Stop condition

Do not build custom billing infrastructure until one of these happens:

- at least one purchase
- three users request Pro access
- one community post drives more than 20 trial runs
