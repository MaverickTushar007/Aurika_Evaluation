# Aurika Production Installation Guide
**One-Command Enterprise Startup**

## 1. Quick Start Installation
To deploy the entire Aurika ecosystem (FastAPI backend, React dashboard, PostgreSQL DB, Redis cache, Prometheus metrics, and Grafana dashboards), execute the following commands on a freshly provisioned Ubuntu machine:

```bash
# 1. Clone the repository and navigate to root
git clone https://github.com/project-aurika/aurika.git
cd aurika

# 2. Configure environment parameters
cp .env.example .env
# Edit .env and supply JWT_SECRET_KEY, groq API key, and DB credentials

# 3. Launch the containerized cluster
docker compose up -d --build
```

---

## 2. Verification Steps
Once launched, verify that all core microservices are online:

- **API Gateway Health:** Connect to `http://localhost:8000/` (Should return `{"status": "ok"}`).
- **Dashboard UI:** Open `http://localhost:5173/` in a web browser.
- **WebSocket Tunnel:** Check connection status in dashboard footer (`ws://localhost:8000/ws` should be connected).
- **Database Persistence:** Verify PostgreSQL container volume is writing data under `pg_data/`.
- **Metrics Monitoring:** Query `http://localhost:9090/` for Prometheus and `http://localhost:3000/` for Grafana panels.
