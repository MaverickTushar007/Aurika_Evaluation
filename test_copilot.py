from datetime import datetime, timezone
from restaurant_analytics.copilot import AICopilot
from restaurant_analytics.restaurant_state import RestaurantSnapshot
from restaurant_analytics.operational_intelligence import OperationalDecision
snapshot = RestaurantSnapshot(
    timestamp=datetime.now(timezone.utc),
    restaurant_status="BUSY",
    current_occupancy=91,
    current_queue_length=8,
    average_wait_time=720.0,
    active_guests=91,
    active_staff=5,
    staff_utilization=99.0,
    zone_status={},
    table_status={},
    host_status={},
    kitchen_status={},
    diagnostic_summary={},
    current_alerts=["QUEUE_SLA_BREACH", "HIGH_OCCUPANCY"],
    health_score=40.0,
    overall_confidence=0.96,
    system_status="DEGRADED"
)
decisions = [
    OperationalDecision(
        decision_id="123",
        title="Guest waiting longer than SLA",
        description="Average wait time exceeds the configured SLA.",
        severity="CRITICAL",
        priority=1,
        confidence=0.96,
        reason="Rule QUEUE_SLA_BREACH triggered by average_wait_time matching condition.",
        supporting_metrics={"average_wait_time": 720.0},
        supporting_events=["QUEUE_SLA_BREACH", "HIGH_OCCUPANCY"],
        recommended_action="Deploy second host or open additional waiting area",
        estimated_impact="Reduces queue time and prevents guest abandonment",
        generated_timestamp=datetime.now(timezone.utc)
    )
]
copilot = AICopilot(snapshot, decisions)
print("Q1:", copilot.answer("waiting_count"))
print("Q2:", copilot.answer("health_status"))
print("Q3:", copilot.answer("top_recommendation"))
print("Q4:", copilot.answer("recommendation_reason"))
print("Q5:", copilot.answer("system_confidence"))
