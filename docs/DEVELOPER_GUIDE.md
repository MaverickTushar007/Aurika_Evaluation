# Aurika Developer Guide

Welcome to the Project Aurika engineering team! This guide will help you get your local environment running and explain the core architecture of the system.

## 1. System Architecture
Aurika operates as an event-driven AI platform. At its core:
1. **Edge Inference Node:** Reads RTSP camera streams, extracts bounding boxes and facial embeddings via TensorRT.
2. **State Bus:** All detections are serialized into Redis.
3. **Digital Twin:** Subscribes to Redis, mapping 2D pixel coordinates into 3D floor plan coordinates (Homography) to build the Restaurant Digital Twin (RDT).
4. **Decision Engine:** Analyzes the RDT to detect anomalies (queue build-ups, dirty tables) and emits recommendations.
5. **Dashboard:** A React/Vite web application that visualizes the RDT and provides actionable alerts to restaurant managers.

## 2. Local Environment Setup

### 2.1 Prerequisites
- Python 3.10+
- Node.js 18.x + npm
- Docker & Docker Compose (for Redis/PostgreSQL)

### 2.2 Bootstrapping
Use the unified `Makefile` to set up your environment:
```bash
make install
```
This command will:
1. Create a Python virtual environment (`.venv`) and install `requirements.txt`.
2. Navigate to `dashboard/` and run `npm ci`.
3. Pull necessary Docker images.

### 2.3 Running the Stack Locally
To run the full stack (API, Mock Cameras, Dashboard) in development mode:
```bash
make run
```
You can access the dashboard at `http://localhost:5173`.

## 3. Development Standards
- **Typing:** We enforce strict type hints via `mypy`.
- **Logging:** Do not use `print()`. Use the configured `logging` module.
- **Testing:** All new logic must be accompanied by a test in the `tests/` directory. Run `make test` before pushing.
