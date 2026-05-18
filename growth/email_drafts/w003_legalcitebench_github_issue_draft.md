# W003 LegalCiteBench GitHub Issue Draft

Status: draft_only_public_post_not_submitted
Target: https://github.com/Sijia711/LegalCiteBench/issues
Prepared: 2026-05-18

## Title

Taxonomy mapping: real citation vs unsupported claim span

## Body

Hi LegalCiteBench team,

I read the LegalCiteBench paper and dataset card. I am building a small complementary source-isolated audit tool, AI Judge Citation Audit, focused on preserving raw model answers, isolated external evidence, and audit verdicts separately.

The overlap I am trying to make precise is the gap between citation reliability and exact claim support:

- `citation_status`: verified / weakly_verified / irrelevant / unverifiable / contradicted
- `source_relevance`: relevant / weakly_relevant / irrelevant / unknown
- `claim_support`: supported / partially_supported / unsupported / contradicted / unknown

The hard case is where a real authority is cited, but the generated proposition overstates what the authority supports. In AI Judge this can be:

```text
citation_status = verified
source_relevance = relevant
claim_support = contradicted
support_failure_code = overclaimed_causation
```

Demo: https://huggingface.co/spaces/reguorier/ai-judge-citation-audit
Spec: https://github.com/reguorier/ai-judge/blob/main/docs/CLAIM_SUPPORT_AUDIT_SPEC.md

Would you be open to a quick taxonomy comparison? I am especially interested in whether AI Judge's claim-support failure codes can map to LegalCiteBench's citation error detection / case verification failure categories, particularly real-citation / wrong-proposition cases.

Best,
Reguorier
