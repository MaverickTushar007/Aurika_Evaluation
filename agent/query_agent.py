from groq import Groq
import sqlite3
import json
import os

api_key = os.environ.get("GROQ_API_KEY")
if api_key:
    client = Groq(api_key=api_key)
else:
    client = None

SCHEMA = """
Tables:
- persons(token_id TEXT, first_seen TEXT, last_seen TEXT, camera_id TEXT, abandoned INTEGER, is_staff INTEGER, staff_id TEXT)
- wait_metrics(id INTEGER, token_id TEXT, entry_time TEXT, exit_time TEXT, wait_seconds REAL, time_to_service REAL, abandoned INTEGER, date TEXT)
- temporal_sessions(session_id TEXT, camera_id TEXT, start_time TEXT, end_time TEXT, duration_seconds REAL)
- business_events(id INTEGER, session_id TEXT, event_type TEXT, timestamp TEXT, value REAL, zone_id TEXT)

Notes:
- abandoned=1 means person left before being attended
- is_staff=1 means person is a staff member, is_staff=0 means customer
- staff_id is the unique identifier of staff members (e.g. emp_mary, emp_jack)
- wait_seconds is total dwell time in the venue
- time_to_service is the time in seconds from when the customer entered to when they were first attended/addressed by a staff member (null if not attended or if staff member)
- dates stored as YYYY-MM-DD strings
- timestamps are ISO8601 UTC strings
- temporal_sessions tracks visitor tracking sessions, duration_seconds is the total visit length.
- business_events logs state changes and zone transitions. event_type values include: 'entered', 'exited', 'enter_zone', 'exit_zone', 'waiting', 'seated', 'left_table'.
"""

SYSTEM = f"""You are a business intelligence assistant for a restaurant/venue analytics platform.
You answer questions by writing SQLite SELECT queries against this schema:

{SCHEMA}

Rules:
- Return ONLY the raw SQL query, nothing else
- No markdown, no explanation, no backticks
- Always use SELECT, never INSERT/UPDATE/DELETE
"""


def ask(question: str, venue_id: str = "default") -> dict:
    db = sqlite3.connect('db/customer_intel.db')

    # ── Inject venue memory context for self-learning awareness ───────────────
    venue_context = ""
    try:
        from db.memory_updater import build_context_snapshot
        venue_context = build_context_snapshot(venue_id=venue_id)
    except Exception:
        pass

    system_with_context = SYSTEM
    if venue_context:
        system_with_context = (
            SYSTEM
            + "\n\nUse this learned venue context when formulating queries — "
            + "it helps you give historically-aware answers:\n\n"
            + venue_context
        )

    if client is None:
        q_lower = question.lower()
        if "total visitors" in q_lower or "how many total" in q_lower:
            sql = "SELECT COUNT(*) as total_visitors FROM persons"
        elif "customers" in q_lower:
            sql = "SELECT COUNT(*) as total_customers FROM persons WHERE is_staff = 0"
        elif "average dwell" in q_lower:
            sql = "SELECT AVG(wait_seconds) as avg_dwell FROM wait_metrics"
        elif "longest" in q_lower:
            sql = "SELECT token_id, MAX(wait_seconds) as max_dwell FROM wait_metrics"
        elif "abandoned" in q_lower:
            sql = "SELECT COUNT(*) as abandoned_count FROM wait_metrics WHERE abandoned = 1"
        elif "staff" in q_lower:
            sql = "SELECT COUNT(DISTINCT staff_id) as active_staff FROM persons WHERE is_staff = 1"
        elif "served" in q_lower:
            sql = "SELECT COUNT(*) as served_count FROM wait_metrics WHERE abandoned = 0"
        elif "busiest" in q_lower:
            sql = "SELECT entry_time, COUNT(*) as count FROM wait_metrics GROUP BY entry_time ORDER BY count DESC LIMIT 1"
        elif "people entered" in q_lower:
            sql = "SELECT COUNT(*) as count FROM business_events WHERE event_type='entered'"
        elif "people exited" in q_lower:
            sql = "SELECT COUNT(*) as count FROM business_events WHERE event_type='exited'"
        elif "people seated" in q_lower:
            sql = "SELECT COUNT(*) as count FROM business_events WHERE event_type='seated'"
        elif "current occupancy" in q_lower:
            sql = "SELECT COUNT(*) as count FROM persons WHERE last_seen IS NULL"
        elif "waiting count" in q_lower:
            sql = "SELECT COUNT(*) as count FROM business_events WHERE event_type='waiting'"
        elif "table occupancy" in q_lower:
            sql = "SELECT COUNT(DISTINCT session_id) as count FROM business_events WHERE event_type='seated'"
        else:
            sql = "SELECT 'Answer unavailable: Required observations not present in available footage' as error"
    else:
        msg = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_with_context},
                {"role": "user", "content": question}
            ],
            max_tokens=256,
            temperature=0
        )
        sql = msg.choices[0].message.content.strip()
    print(f"\nSQL: {sql}\n")
    try:
        cur = db.cursor()
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        result = [dict(zip(cols, r)) for r in rows]
    except Exception as e:
        result = {"error": str(e), "sql": sql}
    finally:
        db.close()
    return result


if __name__ == "__main__":
    questions = [
        # Visitor overview
        "How many total visitors have we had?",
        "How many of those visitors were customers (not staff)?",
        "What is the average dwell time in seconds?",
        "Which person stayed the longest and for how long?",
        # Abandonment
        "How many people abandoned without being served?",
        "What percentage of customers abandoned? Show as a number between 0 and 100.",
        # Staff metrics
        "How many staff members were active?",
        "List all staff IDs that were detected.",
        "What is the average dwell time for staff members?",
        # Service quality
        "What is the average time before a customer is attended by staff?",
        "What is the maximum time a customer waited before being served?",
        "How many customers were successfully served?",
        # Time ranges
        "What was the busiest 10-second window? Show the entry_time and count of people entering.",
        # Self-learning / baseline questions
        "How does today's performance compare to our typical patterns?",
        "Are there any unusual patterns I should know about?",
        "What's our busiest hour historically?",
    ]
    for q in questions:
        print(f"Q: {q}")
        result = ask(q)
        print(f"A: {json.dumps(result, indent=2)}")
        print("-" * 50)
