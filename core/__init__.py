"""AI Judge Core — Multi-model AI jury package v2.1.0.

Public modules (this repository):
  - license_validator: Community license shim
  - hermes_output: Hermes-compatible verdict envelope
  - formula_engine: Phase 1 scoring functions (log_score, allocation_score, etc.)
  - scoring_v2: v2.0 claim and jury scoring pipeline
  - peach_projection: Two Peaches scarcity-based weight allocation
  - schemas: Data contract definitions

Production modules (paid core, not in this repository):
  - jury: Session creation and packet generation
  - collect: Browser/CDP answer collection
  - verdict: Claim scoring and consensus detection
  - reflect: Performance trend analysis
"""

__version__ = "2.1.0"
__author__ = "AI Judge Contributors"
__license__ = "BSL-1.1"
