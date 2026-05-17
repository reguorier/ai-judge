# X / Short-Form Launch Thread

Status: ready for publish queue

## Main Post

```text
I built AI Judge Citation Audit: an open-source tool that catches fabricated, weak, irrelevant, unverifiable, and contradicted citations in AI-generated answers.

The key rule: model-mentioned sources do not verify themselves.

Live demo:
https://huggingface.co/spaces/reguorier/ai-judge-citation-audit

GitHub:
https://github.com/reguorier/ai-judge

Hard benchmark cases:
https://github.com/reguorier/ai-judge/issues/2
```

## Thread

```text
1/ Most AI eval asks: "Was the answer good?"

AI Judge Citation Audit asks a smaller publish-risk question:

Can each citation be trusted from isolated external evidence?
```

```text
2/ The tool keeps four layers separate:

- raw model answer
- model-mentioned candidate sources
- supplied/fetched external evidence
- verification output

That prevents the judge from using hallucinated sources to verify hallucinated claims.
```

```text
3/ Output labels:

verified
weakly_verified
irrelevant
unverifiable
contradicted

Important: unverifiable is not false. It means the audit needs more isolated evidence.
```

```text
4/ The launch benchmark is deliberately small:

100 deterministic cases
no model API required
no browser bridge required

Command:
PYTHONPATH=. python tools/run_citation_bench.py --fail-under 0.95
```

```text
5/ Looking for hard benchmark cases:

- plausible fake papers/reports
- real sources that don't support the claim
- citations that contradict the answer
- AI answers that sound sourced but collapse under inspection
```

## Quote Cards

| Card | Copy | Visual source |
|---|---|---|
| 1 | Model-mentioned sources do not verify themselves. | `product/social_quote_cards.html` |
| 2 | `unverifiable` is not `false`; it is a request for isolated evidence. | `product/social_quote_cards.html` |
| 3 | Citation audit should preserve raw answer, external evidence, and verification output separately. | `product/social_quote_cards.html` |
