# Unverifiable Is Not False

## The distinction

`unverifiable` means the audit does not have enough isolated external evidence to validate a citation.

It does not mean:

- the claim is false
- the source is fake
- the answer is malicious
- the model definitely hallucinated

It means the answer is not ready to trust as a sourced claim.

AI Judge now records a reason code under the main `unverifiable` label. The label stays stable for users, while the reason code explains what kind of missing-evidence event happened.

## Why this matters

Publishing workflows need more than true/false.

An AI answer can cite:

- a plausible source that does not exist
- a real source that does not support the claim
- a source that supports a weaker claim
- a source that contradicts the answer
- a source that cannot be accessed from the current evidence layer

Those cases deserve different labels.

## AI Judge labels

| Label | Meaning |
|---|---|
| `verified` | External evidence strongly supports the citation and claim. |
| `weakly_verified` | Evidence partially supports the citation or lacks a precise anchor. |
| `irrelevant` | The source exists but does not support the cited claim. |
| `unverifiable` | Current isolated evidence is insufficient. |
| `contradicted` | External evidence explicitly refutes the citation or claim. |

## Unverifiable reason codes

| Reason code | Meaning |
|---|---|
| `no_citation` | The answer did not provide a checkable citation. |
| `missing_external_evidence` | No isolated evidence matched the citation. |
| `candidate_not_fetched` | The source was only mentioned by the model and has not been independently fetched or supplied. |
| `fetch_error` | Retrieval failed; this is not proof that the source is fake. |
| `retrieval_blocked` | Access was blocked or permission-gated. |
| `weak_match` | Some evidence matched, but not strongly enough to verify the citation. |

## Evidence provenance

Evidence also keeps a provenance grade:

| Provenance | Meaning |
|---|---|
| `model_candidate` | A source mentioned by the AI answer. It cannot verify itself. |
| `user_supplied` | Evidence supplied by a user or external workflow. Useful, but not equivalent to independent attestation. |
| `fetched` | Evidence fetched by Evidence Broker from the cited URL. |
| `independently_attested` | Evidence with an external attestation or witness ID. |
| `notarized` | Evidence tied to a witness hash, ledger hash, or notarized record. |

## Product rule

Model-mentioned sources do not verify themselves.

The source must enter an isolated evidence layer before it can upgrade a citation.

## Practical policy

- Do not publish `contradicted` claims.
- Review `irrelevant` claims before publishing.
- Treat `unverifiable` as a request for evidence, not as a final accusation.
- Let `weakly_verified` pass only when the risk is low or a human accepts it.
