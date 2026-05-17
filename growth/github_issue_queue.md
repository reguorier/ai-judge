# GitHub Issue Queue: Citation Audit Launch

Status: ready for issue creation confirmation

Target repository:

```text
https://github.com/reguorier/ai-judge
```

## Labels To Ensure

```text
good first benchmark case
citation audit feedback
help wanted
launch feedback
```

Do not create labels or issues until click-time confirmation.

## Issue 1

Title:

```text
Collect hard citation hallucination benchmark cases
```

Labels:

```text
good first benchmark case, citation audit feedback, help wanted
```

Body:

```markdown
AI Judge Citation Audit needs hard benchmark cases that expose citation failure modes.

Useful cases:

- plausible but fake papers, surveys, reports, standards, or institution pages
- real sources that exist but do not support the AI answer's claim
- sources that weakly support a related point but not the stated conclusion
- sources that contradict the AI answer

Please include:

- anonymized AI answer text
- citation or source string
- optional external evidence
- expected label: `verified`, `weakly_verified`, `irrelevant`, `unverifiable`, or `contradicted`
- short reason for the label

The benchmark format is `citation-bench/citation-bench-100.jsonl`.
```

Acceptance:

```text
At least 10 usable new benchmark cases are collected or converted into JSONL.
```

## Issue 2

Title:

```text
Improve the distinction between unverifiable and contradicted citations
```

Labels:

```text
citation audit feedback, help wanted
```

Body:

```markdown
The launch principle is that `unverifiable` is not the same as `false`.

- `unverifiable`: isolated external evidence is not enough to validate the citation.
- `contradicted`: external evidence explicitly refutes the citation or related claim.

This issue tracks edge cases where that boundary is confusing.

Please add examples where:

- a source exists but does not support the exact claim
- evidence partially supports one sentence but not the full conclusion
- a source is stale, superseded, or context-dependent
- the right label is ambiguous

The goal is to improve benchmark coverage and public documentation, not to force every case into a false/true binary.
```

Acceptance:

```text
Document at least 5 edge cases and update docs or benchmark labels if needed.
```

## Issue 3

Title:

```text
Design batch audit for Markdown, PDF, and Docx files
```

Labels:

```text
launch feedback, help wanted
```

Body:

```markdown
The launch version audits Markdown-style inputs and produces HTML/JSON reports.

Potential Pro direction:

- batch Markdown audit
- PDF citation extraction with page anchors
- Docx citation extraction with paragraph anchors
- historical Replay Ledger per file
- exportable Certification ID reports
- GitHub Action artifact output

This issue collects real user needs before implementation.

Please comment with:

- file type you need first: Markdown, PDF, Docx, GitHub PR, or other
- expected input size
- whether network fetch should be allowed
- desired output: HTML, JSON, CSV, SARIF, or CI comment
```

Acceptance:

```text
Collect at least 3 concrete user workflows before building batch audit.
```

## Issue 4

Title:

```text
Add more real-world examples to the demo gallery
```

Labels:

```text
citation audit feedback, good first benchmark case
```

Body:

```markdown
Current demo gallery:

- fake citation
- product plan without evidence
- sounds smart, low judgment

More useful demos would show:

- legal-tech memo citations
- investment memo citations
- medical or health citation disclaimers
- open-source README citations
- AI research paper references

Examples should preserve source isolation:

- raw AI answer
- model-mentioned candidate source
- external evidence
- verification output

No private or sensitive documents should be included without permission.
```

Acceptance:

```text
Add at least 2 new public-safe demo inputs and generated HTML/JSON reports.
```
