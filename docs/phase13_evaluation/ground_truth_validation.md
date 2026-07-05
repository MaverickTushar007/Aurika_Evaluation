# Ground Truth & KPI Validation Logic

## Evaluation Protocol
Whenever annotations exist, the following logic applies:
- **Identity Continuity**: Bounding boxes mapped to global IDs across frames. Evaluated using IDF1.
- **Zone Transitions**: Polygons mapped over frames. A transition is valid if the Track ID enters the polygon geometry.
- **Wait Time**: `ExitTime - EntryTime` for a specific Track ID within the "Queue" zone.
- **Table Turnover**: Duration of continuous occupation of a "Table" polygon by at least one Track ID.

> [!WARNING]
> For datasets lacking restaurant-specific annotations (e.g. CrowdHuman), we will ONLY evaluate core CV metrics (mAP, HOTA). We will **Never fabricate scores** for business KPIs on these datasets.
