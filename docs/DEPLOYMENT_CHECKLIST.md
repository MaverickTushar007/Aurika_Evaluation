# Aurika Go-Live Deployment Checklist
**Final Verification Tasks Prior to Customer Handover**

## 1. Pre-Deployment Configuration
- [ ] Mount hardware edge nodes and secure camera brackets.
- [ ] Set up isolated VLAN for camera network and edge server.
- [ ] Add static IP assignments for all cameras in `configs/cameras.json`.
- [ ] Align coordinate transformations and homographies for all camera views.

## 2. Platform Installation & Boot
- [ ] Install Docker and NVIDIA Container Toolkit on server node.
- [ ] Clone codebase and configure secrets inside `.env` file.
- [ ] Run `docker compose up -d` to spin up containers.
- [ ] Confirm all containers show `Up` using `docker compose ps`.

## 3. Post-Deployment Verification
- [ ] Access the dashboard at `http://localhost:5173/` and verify WebSocket connection status.
- [ ] Trigger mock telemetry generation or play sample camera feeds to verify bounding boxes.
- [ ] Force a camera disconnect by shutting down the RTSP stream; check that the alert is visible on the dashboard within 5 seconds.
- [ ] Confirm database entries are being written to the PostgreSQL volume by checking the `temporal_sessions` table.
