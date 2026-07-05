# Aurika Administrator & Disaster Recovery Guide
**System Maintenance, Backup, and Recovery Runbook**

## 1. System Maintenance
As an administrator, you are responsible for checking system configurations, generating backups, and managing service logs.

---

## 2. Backup & Restore Operations

### 2.1 Database Backup
To create a complete backup snapshot of the PostgreSQL database, execute:
```bash
docker compose exec -t postgres pg_dumpall -c -U postgres > backup_$(date +%F).sql
```

### 2.2 Database Restore
To restore database state from a backup script:
```bash
cat backup_YYYY-MM-DD.sql | docker compose exec -T postgres psql -U postgres
```

### 2.3 Configuration Import/Export
All configurations are stored in the host system under the `configs/` directory. 
- **Export:** Archive the configs directory: `tar -czvf configs_backup.tar.gz configs/`
- **Import:** Extract backup to destination folder: `tar -xzvf configs_backup.tar.gz`

---

## 3. Disaster Recovery Scenario (Power Outage)
If the edge server suffers a power loss:
1. Ensure the UPS backup supplies short-term power to shut down the edge node gracefully.
2. Upon power restoration, the system automatically starts Docker containers via the `restart: always` compose directives.
3. Verification: Ensure all cameras are emitting RTSP signals and verify connection on the Grafana health page.
