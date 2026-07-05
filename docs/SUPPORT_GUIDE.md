# Aurika Troubleshooting & Customer Support Guide
**Shift Diagnostics, Log Collection, and Support Bundles**

## 1. Troubleshooting Common Issues

### 1.1 Camera Disconnect
- **Symptoms:** Bounding boxes missing for a zone; camera status shows `DEGRADED` on dashboard.
- **Action:** Check physical PoE connection. Run ping check: `ping 10.0.54.x`. If host is reachable, restart the tracking service: `docker compose restart tracker`.

### 1.2 Database Read Timeout
- **Symptoms:** Dashboard shows "API Error: Timeout".
- **Action:** Verify database CPU/disk metrics. Check connection limits and pool status. Restart PostgreSQL container: `docker compose restart postgres`.

---

## 2. Generating Support Diagnostic Bundles
When contacting the Aurika Enterprise support team, please generate and supply a diagnostic bundle:

```bash
# 1. Generate system health report and diagnostic summary
docker compose exec api python3 -m pilot.scripts.run_pilot_deployment > system_health.log

# 2. Package logs, configurations, and system health status
tar -czvf aurika_support_bundle.tar.gz \
    system_health.log \
    logs/ \
    configs/ \
    docker-compose.yml
```
Email the resulting archive file `aurika_support_bundle.tar.gz` directly to `enterprise-support@aurika.ai` for expedited root-cause analysis.
