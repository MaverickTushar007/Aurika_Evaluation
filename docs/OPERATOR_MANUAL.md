# Aurika Operator Manual
**Hostess & Server Shift Management Guide**

## 1. Dashboard Overview
The Aurika Dashboard is designed for real-time restaurant monitoring. Operators can manage the entire floor using three primary panels:

- **Seating & Table Availability Grid:** Color-coded layout showing `AVAILABLE` (green), `OCCUPIED` (red), `DIRTY` (yellow), and `RESERVED` (blue) tables.
- **Alert Panel:** Displays high-priority operational issues requiring immediate attention (e.g. *Queue SLA Breach* or *Table 202 Dirty for >8 Mins*).
- **AI Recommendation Engine:** Lists prioritized actions designed to optimize turnover (e.g. *Seat Party of 4 at Table 102*).

---

## 2. Standard Shift Workflows

### 2.1 Seating Guests
1. Look at the **Recommendations** panel for the top seating recommendation.
2. Direct the guest party to the recommended table.
3. Click "Acknowledge" on the recommendation card to clear it from the queue.

### 2.2 Table Cleaning
1. When a table status turns yellow (`DIRTY`), dispatch a busser to clean the table.
2. Once cleaned, the visual tracking cameras will automatically transition the table back to `AVAILABLE`. If camera views are blocked, click the table on the dashboard and select "Mark Available."
