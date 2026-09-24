import sqlite3
import re
from datetime import datetime
from collections import Counter


DATABASE_PATH = "data/intelligence.db"


# ============================================================
# SCORE THRESHOLDS
# ============================================================

BREAKING_SCORE = 80
HIGH_SCORE = 60
MEDIUM_SCORE = 35


# ============================================================
# CRITICAL KEYWORDS
# ============================================================

CRITICAL_KEYWORDS = {

    "imf": 25,
    "default": 30,
    "devaluation": 25,
    "currency crisis": 30,
    "financial crisis": 30,
    "emergency": 20,

    "policy rate": 20,
    "interest rate": 20,

    "sbp": 15,
    "fbr": 15,

    "tax reform": 15,
    "budget": 15,

    "petrol price": 18,
    "electricity tariff": 18,
    "gas tariff": 18,

    "psx crash": 30,
    "market crash": 30,

    "sanctions": 25,
    "war": 30,

    "major agreement": 20,
}


# ============================================================
# IMPORTANT KEYWORDS
# ============================================================

IMPORTANT_KEYWORDS = {

    "inflation": 12,
    "exports": 10,
    "imports": 10,

    "investment": 10,
    "foreign investment": 15,

    "trade deficit": 15,
    "trade surplus": 12,

    "profit": 7,
    "earnings": 7,

    "banking": 8,
    "energy": 8,

    "oil": 8,
    "gas": 8,

    "stock market": 10,
    "kse-100": 12,
    "kse 100": 12,
    "psx": 12,

    "tax": 10,
    "loan": 7,
    "interest": 10,
}


# ============================================================
# EVENT TYPE WEIGHTS
# ============================================================

EVENT_WEIGHTS = {

    "imf": 20,
    "monetary_policy": 20,
    "tax_policy": 18,
    "fiscal_policy": 18,

    "energy": 15,
    "inflation": 15,
    "market_movement": 15,

    "trade": 12,
    "investment": 12,
    "banking": 12,

    "corporate_action": 8,
    "government_decision": 10,

    "general": 0,
}


# ============================================================
# OFFICIAL ENTITIES
# ============================================================

OFFICIAL_ENTITIES = {

    "state bank of pakistan",
    "sbp",

    "federal board of revenue",
    "fbr",

    "pakistan stock exchange",
    "psx",

    "nepra",
    "ogra",
    "securities and exchange commission",
    "secp",

    "ministry of finance",
    "ministry of commerce",

    "government of pakistan",
    "cabinet",
}


# ============================================================
# DATABASE SETUP / MIGRATION
# ============================================================

def ensure_alerts_table(db):

    # --------------------------------------------------------
    # Create the original table if it does not exist
    # --------------------------------------------------------

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS alerts (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            event_id INTEGER,

            alert_type TEXT,

            channel_id TEXT,

            sent_at TIMESTAMP

        )
        """
    )

    db.commit()

    # --------------------------------------------------------
    # Read existing columns
    # --------------------------------------------------------

    rows = db.execute(
        "PRAGMA table_info(alerts)"
    ).fetchall()

    existing_columns = {
        row[1]
        for row in rows
    }

    # --------------------------------------------------------
    # Additional intelligence columns
    # --------------------------------------------------------

    migrations = {

        "severity":
            "ALTER TABLE alerts ADD COLUMN severity TEXT",

        "score":
            "ALTER TABLE alerts ADD COLUMN score INTEGER DEFAULT 0",

        "headline":
            "ALTER TABLE alerts ADD COLUMN headline TEXT",

        "reason":
            "ALTER TABLE alerts ADD COLUMN reason TEXT",

        "category":
            "ALTER TABLE alerts ADD COLUMN category TEXT",

        "direction":
            "ALTER TABLE alerts ADD COLUMN direction TEXT",

        "published_at":
            "ALTER TABLE alerts ADD COLUMN published_at TEXT",

        "status":
            "ALTER TABLE alerts ADD COLUMN status TEXT DEFAULT 'pending'",

        "created_at":
            "ALTER TABLE alerts ADD COLUMN created_at TIMESTAMP",

    }

    # --------------------------------------------------------
    # Apply missing columns
    # --------------------------------------------------------

    added = 0

    for column, sql in migrations.items():

        if column not in existing_columns:

            db.execute(sql)

            added += 1

            print(
                f"[SYSTEM] Added alerts column: {column}"
            )

    db.commit()

    if added:

        print(
            f"[SYSTEM] Alerts schema upgraded: "
            f"{added} columns added."
        )

    else:

        print(
            "[SYSTEM] Alerts schema already up to date."
        )


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize(text):

    if not text:

        return ""

    text = str(text).lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# KEYWORD SCORING
# ============================================================

def keyword_score(text):

    score = 0

    matched = []

    for keyword, weight in (
        CRITICAL_KEYWORDS.items()
    ):

        if keyword in text:

            score += weight

            matched.append(
                keyword
            )

    for keyword, weight in (
        IMPORTANT_KEYWORDS.items()
    ):

        if keyword in text:

            score += weight

            matched.append(
                keyword
            )

    return score, matched


# ============================================================
# EVENT TYPE SCORE
# ============================================================

def event_type_score(event_type):

    return EVENT_WEIGHTS.get(
        event_type,
        0
    )


# ============================================================
# IMPORTANCE SCORE
# ============================================================

def importance_score(importance):

    try:

        importance = int(
            importance
        )

    except Exception:

        importance = 1

    return importance * 10


# ============================================================
# OFFICIAL ENTITY SCORE
# ============================================================

def official_entity_score(text):

    for entity in OFFICIAL_ENTITIES:

        if entity in text:

            return 15

    return 0


# ============================================================
# SEVERITY
# ============================================================

def severity_from_score(score):

    if score >= BREAKING_SCORE:

        return "BREAKING"

    if score >= HIGH_SCORE:

        return "HIGH"

    if score >= MEDIUM_SCORE:

        return "MEDIUM"

    return "LOW"


# ============================================================
# BUILD ALERT
# ============================================================

def build_alert(
    event,
    analysis
):

    # --------------------------------------------------------
    # Headline
    # --------------------------------------------------------

    headline = ""

    if (
        "headline" in event.keys()
        and event["headline"]
    ):

        headline = event["headline"]

    elif (
        "title" in event.keys()
        and event["title"]
    ):

        headline = event["title"]

    # --------------------------------------------------------
    # Event type
    # --------------------------------------------------------

    event_type = (

        event["event_type"]

        if (
            "event_type" in event.keys()
            and event["event_type"]
        )

        else "general"
    )

    # --------------------------------------------------------
    # Direction
    # --------------------------------------------------------

    direction = (

        analysis["direction"]

        if (
            "direction" in analysis.keys()
            and analysis["direction"]
        )

        else "neutral"
    )

    # --------------------------------------------------------
    # Combine event text
    # --------------------------------------------------------

    values = []

    for key in event.keys():

        value = event[key]

        if value is not None:

            values.append(
                str(value)
            )

    combined_text = normalize(
        " ".join(values)
    )

    # --------------------------------------------------------
    # Base score
    # --------------------------------------------------------

    score = 0

    reasons = []

    # --------------------------------------------------------
    # Keyword score
    # --------------------------------------------------------

    keyword_points, matched = keyword_score(
        combined_text
    )

    score += keyword_points

    if matched:

        reasons.append(
            "High-impact terms: "
            + ", ".join(
                matched[:8]
            )
        )

    # --------------------------------------------------------
    # Event type
    # --------------------------------------------------------

    event_points = event_type_score(
        event_type
    )

    score += event_points

    if event_points:

        reasons.append(
            f"Event type: {event_type}"
        )

    # --------------------------------------------------------
    # Analytical importance
    # --------------------------------------------------------

    importance = (

        analysis["importance"]

        if (
            "importance" in analysis.keys()
            and analysis["importance"]
        )

        else 1
    )

    importance_points = importance_score(
        importance
    )

    score += importance_points

    if importance >= 4:

        reasons.append(
            f"High analytical importance: "
            f"{importance}/5"
        )

    # --------------------------------------------------------
    # Official entity
    # --------------------------------------------------------

    official_points = official_entity_score(
        combined_text
    )

    score += official_points

    if official_points:

        reasons.append(
            "Official institution involved"
        )

    # --------------------------------------------------------
    # Direction
    # --------------------------------------------------------

    if direction in (
        "positive",
        "negative",
    ):

        score += 5

        reasons.append(
            f"Detected direction: {direction}"
        )

    # --------------------------------------------------------
    # Cap
    # --------------------------------------------------------

    score = min(
        score,
        100
    )

    # --------------------------------------------------------
    # Severity
    # --------------------------------------------------------

    severity = severity_from_score(
        score
    )

    # --------------------------------------------------------
    # Alert type
    # --------------------------------------------------------

    if severity == "BREAKING":

        alert_type = "breaking_news"

    elif severity == "HIGH":

        alert_type = "high_importance"

    elif severity == "MEDIUM":

        alert_type = "important_news"

    else:

        alert_type = "news"

    # --------------------------------------------------------
    # Reason
    # --------------------------------------------------------

    reason = "; ".join(
        reasons
    )

    if not reason:

        reason = (
            "Classified using the "
            "ASNA importance engine."
        )

    # --------------------------------------------------------
    # Published date
    # --------------------------------------------------------

    published_at = None

    if "published_at" in event.keys():

        published_at = (
            event["published_at"]
        )

    return {

        "event_id":
            event["id"],

        "alert_type":
            alert_type,

        "severity":
            severity,

        "score":
            score,

        "headline":
            headline,

        "reason":
            reason,

        "category":
            event_type,

        "direction":
            direction,

        "published_at":
            published_at,

    }


# ============================================================
# DUPLICATE CHECK
# ============================================================

def alert_exists(
    db,
    event_id
):

    row = db.execute(
        """
        SELECT id
        FROM alerts
        WHERE event_id = ?
        LIMIT 1
        """,
        (
            event_id,
        )
    ).fetchone()

    return row is not None


# ============================================================
# SAVE ALERT
# ============================================================

def save_alert(
    db,
    alert
):

    db.execute(
        """
        INSERT INTO alerts (

            event_id,
            alert_type,
            severity,
            score,
            headline,
            reason,
            category,
            direction,
            published_at,
            status,
            created_at

        )

        VALUES (
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?
        )
        """,
        (

            alert["event_id"],

            alert["alert_type"],

            alert["severity"],

            alert["score"],

            alert["headline"],

            alert["reason"],

            alert["category"],

            alert["direction"],

            alert["published_at"],

            "pending",

            datetime.now().isoformat(
                timespec="seconds"
            ),

        )
    )


# ============================================================
# MAIN ENGINE
# ============================================================

def run_alert_engine():

    db = sqlite3.connect(
        DATABASE_PATH
    )

    db.row_factory = sqlite3.Row

    print()
    print("=" * 70)
    print("ASNA IMPORTANCE & BREAKING NEWS ENGINE")
    print("=" * 70)

    # --------------------------------------------------------
    # Verify events table
    # --------------------------------------------------------

    tables = {
        row[0]
        for row in db.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            """
        ).fetchall()
    }

    if "events" not in tables:

        print(
            "[ERROR] events table does not exist."
        )

        print(
            "Run:"
        )

        print(
            "python news/event_engine.py"
        )

        db.close()

        return

    # --------------------------------------------------------
    # Verify analyses table
    # --------------------------------------------------------

    if "analyses" not in tables:

        print(
            "[ERROR] analyses table does not exist."
        )

        print(
            "Run:"
        )

        print(
            "python news/impact_engine.py"
        )

        db.close()

        return

    # --------------------------------------------------------
    # Upgrade alerts table
    # --------------------------------------------------------

    ensure_alerts_table(
        db
    )

    # --------------------------------------------------------
    # Load events + analysis
    # --------------------------------------------------------

    events = db.execute(
        """
        SELECT
            e.*,

            a.direction AS analysis_direction,

            a.importance AS analysis_importance,

            a.confidence AS analysis_confidence

        FROM events e

        LEFT JOIN analyses a
            ON a.event_id = e.id

        ORDER BY e.id ASC
        """
    ).fetchall()

    print()
    print(
        f"Events found: {len(events)}"
    )

    if not events:

        print(
            "[INFO] No events available."
        )

        db.close()

        return

    # --------------------------------------------------------
    # Counters
    # --------------------------------------------------------

    created = 0

    skipped = 0

    errors = 0

    severity_counter = Counter()

    type_counter = Counter()

    # --------------------------------------------------------
    # Process events
    # --------------------------------------------------------

    for index, event in enumerate(
        events,
        start=1
    ):

        # ----------------------------------------------------
        # Duplicate check
        # ----------------------------------------------------

        if alert_exists(
            db,
            event["id"]
        ):

            skipped += 1

            continue

        # ----------------------------------------------------
        # Analysis data
        # ----------------------------------------------------

        analysis = {

            "direction":
                event["analysis_direction"]
                or "neutral",

            "importance":
                event["analysis_importance"]
                or 1,

        }

        try:

            alert = build_alert(
                event,
                analysis
            )

            save_alert(
                db,
                alert
            )

            created += 1

            severity_counter[
                alert["severity"]
            ] += 1

            type_counter[
                alert["alert_type"]
            ] += 1

            print(
                f"[{index}/{len(events)}] "
                f"{alert['severity']:8} | "
                f"{alert['score']:3}/100 | "
                f"{alert['category']:22} | "
                f"{alert['headline'][:55]}"
            )

        except Exception as error:

            errors += 1

            print(
                f"[ERROR] Event "
                f"{event['id']}: "
                f"{error}"
            )

    # --------------------------------------------------------
    # Commit
    # --------------------------------------------------------

    db.commit()

    # --------------------------------------------------------
    # Final report
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("IMPORTANCE ENGINE COMPLETE")
    print("=" * 70)

    print(
        f"Alerts created:       {created}"
    )

    print(
        f"Already existing:     {skipped}"
    )

    print(
        f"Errors:               {errors}"
    )

    print()
    print("SEVERITY DISTRIBUTION")

    if severity_counter:

        for severity, count in (
            severity_counter.most_common()
        ):

            print(
                f"{severity:20} {count}"
            )

    else:

        print(
            "No new alerts."
        )

    print()
    print("ALERT TYPES")

    if type_counter:

        for alert_type, count in (
            type_counter.most_common()
        ):

            print(
                f"{alert_type:25} {count}"
            )

    else:

        print(
            "No new alert types."
        )

    print()
    print(
        "Database table: alerts"
    )

    print(
        f"Completed: "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    print("=" * 70)

    db.close()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    run_alert_engine()