# Aurika Technical Debt Registry

## 1. Split API Gateway Entry Points
- **Debt:** There are three separate, running backend server entry points:
  1. `server.py`: Hosts basic video upload, stats, and `/ask` queries.
  2. `api/main.py`: Re-implements database creation, JWT, upload, and `/ask` queries on different routes.
  3. `analytics_api.py`: Implements BI summaries, heatmaps, and analytics exports.
- **Consequence:** Modifying a database schema or fixing an endpoint requires editing three distinct codebases.

## 2. Empty Decision Engine Stub
- **Debt:** The primary entry point for the Decision & Optimization Engine (`decision_engine/engine.py`) has an empty `evaluate_state` method:
  ```python
  def evaluate_state(self):
      # Will be fleshed out with rule_engine and optimizer calls
      pass
  ```
- **Consequence:** The main orchestrator does nothing. Instead, developers must invoke the lower-level `RecommendationEngine` directly, bypassing the intended modular architecture.

## 3. Ephemeral In-Memory State Managers
- **Debt:** Class patterns like `OperatorFeedbackCollector` and `IncidentManager` store logs in standard Python lists.
- **Consequence:** These lists are not written to SQLite or any database. All operator feedback history is lost the moment the FastAPI server processes restart.
