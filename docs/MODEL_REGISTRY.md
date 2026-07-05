# Enterprise Model Registry & Rollback Manager

The Model Registry (`continuous_learning/model_registry/`) provides enterprise version control, deployment logging, and 1-click rollback across perception, tracking, ReID, forecasting, and decision engines.

## Strict Human-In-The-Loop Guardrail
To prevent catastrophic model degradation or autonomous oscillation:
- **Zero Auto-Deployment**: Models trained on auto-curated datasets are registered with initial status `CANDIDATE`.
- **Mandatory Review**: Candidate models are automatically submitted to the `Human Review Queue` under `MODEL_PROMOTION`.
- **Operator Sign-Off**: A candidate model can ONLY transition to `PRODUCTION` when a human operator explicitly approves the review item or initiates promotion via the enterprise dashboard.

## Model Catalog Lifecycle
1. **`CANDIDATE`**: Newly registered model awaiting shadow evaluation and human review.
2. **`SHADOW`**: Active evaluation version executing alongside production to compute benchmark deltas without affecting downstream decisions.
3. **`PRODUCTION`**: Active live model driving operational recommendations and real-time inference.
4. **`ARCHIVED`**: Previously deployed production model retained for instant rollback.
5. **`REJECTED`**: Candidate model that failed benchmark evaluation or was declined by an operator.

## 1-Click Rollback
If a newly promoted model exhibits unexpected real-world edge case failures, operators can execute 1-click rollback via the dashboard or API (`POST /api/v1/learning/models/rollback`). The system instantly restores the latest `ARCHIVED` version to `PRODUCTION` status and logs an immutable audit entry in the deployment history.
