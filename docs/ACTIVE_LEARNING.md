# Active Learning Sample Ranking & Training Curation

The Active Learning engine (`continuous_learning/active_learning/`) evaluates raw production failures, tracking anomalies, and operator manual corrections to filter high-value samples for training dataset curation and human review.

## Composite Priority Scoring Methodology
Samples are ranked using a multi-criteria weighted formula:
$$\text{Priority Score} = 0.40 \times \text{Business Impact} + 0.30 \times \text{Uncertainty} + 0.20 \times \text{Novelty} + 0.10 \times (1.0 - \text{Confidence})$$

### 1. Business Impact ($40\%$)
- Directly incorporates business severity (e.g., identity switch on a VIP table guest $= 0.95$, queue wait forecast error $>15$ mins $= 0.85$).
- Ensures high-value operational failures receive priority inspection.

### 2. Model Uncertainty ($30\%$)
- Evaluated based on boundary confidence proximity: $\text{Uncertainty} = 1.0 - 2 \times |\text{confidence} - 0.5|$.
- Multi-modal fusion conflicts and camera handover splits automatically receive an boosted uncertainty floor ($\ge 0.85$).

### 3. Novelty & Edge Cases ($20\%$)
- Flags rare failure categories (`HANDOVER_FAILURE`, `FRAGMENTATION`, `FUSION_CONFLICT`) and operator manual overrides as high novelty ($\ge 0.85$).

### 4. Inverse Confidence ($10\%$)
- Low confidence detections are prioritized to strengthen detector robustness against severe occlusions and lighting extremes.

## Curation Recommendations
- **`SEND_TO_REVIEW`** ($\text{Score} \ge 0.45$): Pushed immediately into the `Human Review Queue`.
- **`AUTO_CURATE`** ($0.30 \le \text{Score} < 0.45$): Recommended for batch dataset inclusion.
- **`LOW_PRIORITY_DISCARD`** ($\text{Score} < 0.30$): Discarded to prevent dataset bloat and redundancy.
