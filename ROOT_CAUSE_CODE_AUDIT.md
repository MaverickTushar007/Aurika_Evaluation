# ROOT CAUSE CODE AUDIT
**Prepared By:** Senior Software Debugging Engineer  
**Date:** July 4, 2026

## Overview
I have conducted a rigorous, code-level verification of the claims made in the recent Digital Forensic Audit. I traced the execution path for every suspected bug directly through the source code.

The results are definitive: **Most of the forensic conclusions were factually incorrect and not grounded in the actual codebase.**

---

### 1. Wait Time Aggregation
**Forensic Claim:** "The pipeline is calculating an Exponential Moving Average (EMA) of wait times... smoothing out outliers."
**Verdict:** **FALSE**

**File Path:** `restaurant_analytics/operational_state_engine.py`
**Function:** `_build_snapshot(self)`
**Relevant Code Snippet (Lines 62-70):**
```python
        # Determine average wait time from active waiting guests
        wait_times = []
        active_guests = [v for v in self.metrics_engine.visit_manager.active_visits.values() if v.role == "guest"]
        for g in active_guests:
            m = self.metrics_engine.get_guest_metrics(g.visit_id)
            if "waiting_time_seconds" in m and m["waiting_time_seconds"].value > 0:
                wait_times.append(m["waiting_time_seconds"].value)
        
        avg_wait = sum(wait_times) / len(wait_times) if wait_times else 0.0
```
**Execution Trace & Explanation:**
The `OperationalStateEngine` extracts the `waiting_time_seconds` from the `MetricsEngine` only for guests currently residing in `active_visits`. It then computes a pure arithmetic mean (`sum() / len()`). 
**Why the Forensic Auditor was wrong:** There is no EMA applied to wait times. The discrepancy (142s reported vs 210s historical average) exists because the system only averages the wait times of guests *currently standing in the queue*. Once a guest is seated (or leaves), their wait time drops out of the instantaneous `avg_wait` calculation for the live snapshot.
**Confidence:** 100%

---

### 2. Staff Utilization
**Forensic Claim:** "The engine aggregates staff_count globally instead of isolating roles, artificially dropping the score when non-host staff are idle."
**Verdict:** **TRUE**

**File Path:** `restaurant_analytics/metrics_engine.py`
**Function:** `get_staff_metrics(self)`
**Relevant Code Snippet (Lines 94-101):**
```python
        active_staff = [v for v in self.visit_manager.active_visits.values() if v.role == "staff"]
        staff_count = len(active_staff)
        idle_staff = [v for v in active_staff if v.current_state == StaffState.IDLE.value]
        
        utilization = 0.0
        if staff_count > 0:
            utilization = ((staff_count - len(idle_staff)) / staff_count) * 100
```
**Execution Trace & Explanation:**
The code filters `active_visits` strictly by `v.role == "staff"`. It makes no distinction between "host", "waiter", or "cleaner". It mathematically calculates a single, global utilization score.
**Why the bug occurs:** Hardcoded assumption that all staff members share a single utilization pool.
**Smallest Safe Fix:** Add `role_subtype` filtering to `get_staff_metrics()` to return a dictionary of utilization percentages grouped by specific staff roles.
**Confidence:** 100%

---

### 3. Operational Intelligence Rule Engine
**Forensic Claim:** "The Operational Intelligence mapping dictionary triggers global rules based on arbitrary array lengths... it triggered sending Waiter 2 on break."
**Verdict:** **FALSE**

**File Path:** `configs/rules.json` & `restaurant_analytics/operational_intelligence.py`
**Function:** `_evaluate_condition(self, condition, snapshot)`
**Execution Trace & Explanation:**
The `OperationalIntelligenceLayer` dynamically loads rule templates from `configs/rules.json`. It evaluates conditions against global snapshot properties using `getattr(snapshot, metric_name)`. 
**Why the Forensic Auditor was wrong:** The rule engine does indeed evaluate global metrics. However, **there is no rule in `rules.json` that recommends sending a Waiter on break.** The rules dictate actions like "Deploy second host" or "Prepare kitchen for peak volume". The forensic auditor hallucinated the "Send Waiter 2 on Break" recommendation; the codebase contains no such logic.
**Confidence:** 100%

---

### 4. Role Assignment (The Cleaner Bug)
**Forensic Claim:** "If the probabilistic role classifier fluctuates mid-track, the VisitManager spawns a ghost visit and inflates footfall metrics."
**Verdict:** **FALSE**

**File Path:** `restaurant_analytics/visit_manager.py`
**Function:** `update_visit_role(self, track_id, new_role, timestamp)`
**Relevant Code Snippet (Lines 224-227):**
```python
    def update_visit_role(self, track_id: str, new_role: str, timestamp: datetime):
        visit = self.get_visit(track_id)
        if visit and visit.role != new_role:
            visit.update_role(new_role, timestamp)
```
**Execution Trace & Explanation:**
When a track changes roles (e.g., from "staff" to "guest"), the `VisitManager` calls `update_visit_role`. This simply appends a "role_change" event to the `Visit`'s timeline and updates the `role` property in place. It **does not** instantiate a new `Visit` object. Furthermore, `EventEngine.publish_visit_created()` only emits a `GuestEntered` business event at the exact moment of track creation (`handle_track_start`). Mid-track role updates do not retroactively trigger `GuestEntered` events.
**Why the Forensic Auditor was wrong:** The system architecture makes footfall inflation via mid-track role changes impossible. The +1 occupancy discrepancy observed in the mock OAT data was likely caused by a completely separate tracking fragmentation issue (e.g., track ID loss exceeding the 30-second cache), not a role change.
**Confidence:** 100%
