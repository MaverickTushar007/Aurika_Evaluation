# Contributing to Project Aurika

We adhere to rigorous engineering standards for Project Aurika. Please read these guidelines carefully before submitting a pull request.

## 1. Zero New Abstractions Rule
Aurika's core architecture is complete. **Do not introduce new abstract base classes, managers, or engines.** Your goal is to improve performance, maintainability, and stability within the existing boundaries. If you believe a new subsystem is required, you must submit a formal RFC (Request for Comments) first.

## 2. Branching Strategy
We follow a standard Git Feature Branch Workflow:
- `main` is always production-ready and passing CI.
- Create feature branches off `main` (e.g., `feat/improve-reid-batching` or `fix/patio-camera-memory-leak`).
- Squash commits before opening a PR.

## 3. Pull Request Standards
Every Pull Request must include:
1. **Evidence of Testing:** You must provide proof (e.g., `make test` output) that you haven't broken existing pipelines.
2. **Performance Impact:** If modifying the Tracking Pipeline or Decision Engine, include profiling evidence demonstrating latency/memory impact.
3. **No Dead Code:** Ensure all removed/deprecated code is entirely stripped from the codebase.

## 4. Linting & Formatting
Our CI pipeline will reject your code if it fails linting. We use:
- `black` (line length 100)
- `flake8`
- `isort`
Install our pre-commit hooks via `pre-commit install` to automate this workflow.
