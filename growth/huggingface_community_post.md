# Hugging Face Community Post: Citation Audit Launch

Status: ready for publish confirmation

Target:

```text
https://huggingface.co/spaces/reguorier/ai-judge-citation-audit/discussions
```

## Title

```text
AI Judge Citation Audit: a tiny benchmark + Space for hallucinated citations
```

## Post

```text
I am launching AI Judge Citation Audit, a local-first citation auditor for AI-generated answers.

The Space lets you paste an AI-generated answer and optional external evidence. It separates:

- raw model answer text
- model-mentioned candidate sources
- supplied or fetched external evidence
- verification output

Then it returns citation-level labels:

verified / weakly_verified / irrelevant / unverifiable / contradicted

The design rule is simple: model-mentioned sources do not verify themselves. A URL inside the AI answer is only a candidate source until isolated external evidence supports it.

The first benchmark is intentionally small and deterministic: 100 cases covering the five status labels, no model API required.

Space:
https://huggingface.co/spaces/reguorier/ai-judge-citation-audit

GitHub:
https://github.com/reguorier/ai-judge

Benchmark command:
PYTHONPATH=. python tools/run_citation_bench.py --fail-under 0.95

Demo command:
PYTHONPATH=. python cli/main.py audit examples/fake-citation.md --html reports/fake-citation-audit.html --json reports/fake-citation-audit.json

I am looking for community benchmark cases: fake citations, real citations that do not support the claim, and claims that sound sourced but collapse when evidence is isolated.
```

## Verification Evidence

- Space status: live and manually verified.
- Root app: `https://reguorier-ai-judge-citation-audit.hf.space/?__theme=light`
- Default audit returns `unverifiable`, `needs_more_evidence`, Certification ID, and Replay Ledger hash.
- Benchmark: `100/100` passing via `python3 tools/run_citation_bench.py --fail-under 0.95`.
- Unit tests: `tests/test_citation_audit.py` has `4 passed`.
- Screenshot: `assets/citation-audit-space-output.png`.

## Publish Checklist

- Confirm Hugging Face token `ai-judge-space-deploy-2` has been deleted from settings.
- Open the Space discussion page.
- Create a new discussion with the title and post above.
- Do not post until final click-time confirmation.
- After posting, record the URL in `growth/feedback_log.md`.

## First Replies

If someone asks how this differs from RAG eval tools:

```text
AI Judge Citation Audit is narrower than general RAG/LLM eval. It targets the publish-before-trust moment: an AI answer has citations, and you need to know which citations are externally supported, weak, irrelevant, unverifiable, or contradicted. The core rule is source isolation: URLs mentioned by the model are candidates, not proof.
```

If someone asks why `unverifiable` is not `false`:

```text
Because missing evidence is not contradiction. `unverifiable` means the audit does not have enough isolated external evidence to validate the citation. It becomes `contradicted` only when external evidence explicitly refutes the citation or related claim.
```

If someone asks what to contribute:

```text
The most useful contribution is benchmark cases: AI answers with plausible fake citations, real sources that do not support the claim, or sources that contradict the answer.
```
