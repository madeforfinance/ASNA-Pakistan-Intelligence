import sqlite3
import re
from collections import Counter

DATABASE_PATH = "data/intelligence.db"


# ============================================================
# EVENT TYPES
# ============================================================

EVENT_RULES = {

    "monetary_policy": [
        "policy rate",
        "interest rate",
        "monetary policy",
        "sbp rate",
        "discount rate",
        "rate cut",
        "rate hike",
        "rate unchanged",
        "policy rate unchanged",
    ],

    "inflation": [
        "inflation",
        "cpi",
        "consumer price",
        "price increase",
        "price hike",
        "prices increased",
        "inflation rate",
    ],

    "tax_policy": [
        "fbr",
        "income tax",
        "sales tax",
        "withholding tax",
        "tax rate",
        "tax collection",
        "tax policy",
        "tax amendment",
        "customs duty",
        "tax reform",
    ],

    "fiscal_policy": [
        "budget",
        "fiscal policy",
        "government spending",
        "public expenditure",
        "revenue target",
        "fiscal deficit",
        "budget deficit",
    ],

    "energy": [
        "electricity tariff",
        "power tariff",
        "gas tariff",
        "petrol price",
        "petrol prices",
        "diesel price",
        "oil price",
        "lng",
        "lpg",
        "nepra",
        "ogra",
        "power generation",
        "electricity price",
    ],

    "trade": [
        "exports",
        "export growth",
        "imports",
        "import growth",
        "trade deficit",
        "trade surplus",
        "tariff",
        "customs",
        "trade agreement",
        "trade policy",
    ],

    "investment": [
        "investment",
        "foreign investment",
        "fdi",
        "investor",
        "investment agreement",
        "investment deal",
    ],

    "market_movement": [
        "psx",
        "kse-100",
        "kse 100",
        "stock market",
        "shares",
        "stocks",
        "index",
        "market gained",
        "market fell",
        "market closed",
        "trading session",
    ],

    "banking": [
        "bank",
        "banking",
        "loan",
        "lending",
        "deposit",
        "credit",
        "banking policy",
    ],

    "corporate_action": [
        "acquisition",
        "merger",
        "takeover",
        "dividend",
        "profit",
        "loss",
        "earnings",
        "new plant",
        "expansion",
        "ceo",
        "revenue",
        "quarterly results",
    ],

    "imf": [
        "imf",
        "international monetary fund",
        "extended fund facility",
        "standby arrangement",
        "staff level agreement",
        "loan tranche",
        "imf programme",
        "imf program",
    ],

    "government_decision": [
        "cabinet",
        "government approved",
        "government announces",
        "ministry approved",
        "notification",
        "ordinance",
        "regulation",
        "policy approved",
    ],

}


# ============================================================
# ACTION RULES
# ============================================================

ACTION_RULES = {

    "increase": [
        "increase",
        "increased",
        "increase in",
        "rise",
        "rose",
        "higher",
        "hike",
        "hiked",
        "surge",
        "surged",
        "jump",
        "jumped",
        "grew",
        "growth",
    ],

    "decrease": [
        "decrease",
        "decreased",
        "decline",
        "declined",
        "fall",
        "fell",
        "lower",
        "cut",
        "cutting",
        "reduction",
        "reduced",
        "drop",
        "dropped",
        "slump",
    ],

    "approval": [
        "approved",
        "approval",
        "allowed",
        "cleared",
        "endorsed",
        "sanctioned",
    ],

    "announcement": [
        "announced",
        "announces",
        "announcing",
        "notified",
        "notification",
        "revealed",
        "introduced",
        "unveiled",
    ],

    "agreement": [
        "agreement",
        "agreed",
        "deal",
        "accord",
        "pact",
        "signed",
        "signing",
    ],

    "unchanged": [
        "unchanged",
        "maintained",
        "kept unchanged",
        "no change",
        "left unchanged",
        "remained unchanged",
    ],

    "rejection": [
        "rejected",
        "rejection",
        "denied",
        "refused",
        "blocked",
    ],

}


# ============================================================
# SECTOR RULES
# ============================================================

SECTOR_RULES = {

    "banking": [
        "bank",
        "banking",
        "loan",
        "credit",
        "deposit",
        "sbp",
        "interest rate",
    ],

    "energy": [
        "oil",
        "gas",
        "petrol",
        "diesel",
        "electricity",
        "power",
        "lng",
        "lpg",
        "nepra",
        "ogra",
    ],

    "manufacturing": [
        "factory",
        "manufacturing",
        "cement",
        "textile",
        "steel",
        "automobile",
        "industry",
        "industrial",
    ],

    "technology": [
        "technology",
        "software",
        "digital",
        "ai",
        "artificial intelligence",
        "fintech",
        "telecom",
        "5g",
    ],

    "retail": [
        "retail",
        "consumer",
        "shopping",
        "sales",
        "stores",
        "supermarket",
    ],

    "real_estate": [
        "property",
        "real estate",
        "housing",
        "construction",
        "housing scheme",
    ],

    "agriculture": [
        "agriculture",
        "farmer",
        "crop",
        "wheat",
        "rice",
        "cotton",
        "fertilizer",
        "livestock",
    ],

    "trade": [
        "export",
        "import",
        "customs",
        "trade",
        "shipment",
        "tariff",
    ],

    "markets": [
        "psx",
        "stock",
        "stocks",
        "shares",
        "kse",
        "equity",
        "index",
    ],

    "government": [
        "government",
        "ministry",
        "cabinet",
        "fbr",
        "policy",
        "regulation",
        "notification",
    ],

}


# ============================================================
# ENTITY RULES
# ============================================================

ENTITY_RULES = {

    "State Bank of Pakistan": [
        "sbp",
        "state bank of pakistan",
    ],

    "Federal Board of Revenue": [
        "fbr",
        "federal board of revenue",
    ],

    "Pakistan Stock Exchange": [
        "psx",
        "pakistan stock exchange",
        "kse-100",
        "kse 100",
    ],

    "IMF": [
        "imf",
        "international monetary fund",
    ],

    "NEPRA": [
        "nepra",
        "national electric power regulatory authority",
    ],

    "OGRA": [
        "ogra",
        "oil and gas regulatory authority",
    ],

    "Government of Pakistan": [
        "government of pakistan",
        "federal government",
        "government",
    ],

    "Ministry of Finance": [
        "ministry of finance",
        "finance ministry",
    ],

    "Ministry of Commerce": [
        "ministry of commerce",
        "commerce ministry",
    ],

}


# ============================================================
# HELPERS
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


def detect_from_rules(text, rules):

    scores = Counter()

    for label, keywords in rules.items():

        for keyword in keywords:

            keyword = keyword.lower()

            if keyword in text:

                # Longer phrases receive more weight.
                scores[label] += max(
                    1,
                    len(keyword.split())
                )

    if not scores:
        return "general"

    return scores.most_common(1)[0][0]


def detect_entity(text):

    scores = Counter()

    for entity, keywords in ENTITY_RULES.items():

        for keyword in keywords:

            if keyword.lower() in text:

                scores[entity] += max(
                    1,
                    len(keyword.split())
                )

    if not scores:
        return "Pakistan"

    return scores.most_common(1)[0][0]


def detect_importance(text):

    high_terms = [
        "imf",
        "default",
        "policy rate",
        "interest rate",
        "fbr",
        "sbp",
        "inflation",
        "petrol price",
        "electricity tariff",
        "tax rate",
        "devaluation",
        "rupee",
        "psx crash",
        "market crash",
        "budget",
        "fiscal deficit",
    ]

    medium_terms = [
        "investment",
        "exports",
        "imports",
        "profit",
        "banking",
        "energy",
        "trade",
        "stock market",
        "dividend",
        "earnings",
    ]

    high = sum(
        1
        for keyword in high_terms
        if keyword in text
    )

    medium = sum(
        1
        for keyword in medium_terms
        if keyword in text
    )

    if high >= 2:
        return 5

    if high == 1:
        return 4

    if medium >= 2:
        return 3

    if medium == 1:
        return 2

    return 1


def detect_direction(event_type, action):

    if action == "unchanged":
        return "neutral"

    if action == "rejection":
        return "negative"

    if action in (
        "approval",
        "agreement",
    ):
        return "positive"

    # Price increases are generally negative
    # for consumers/business cost bases.
    if event_type in (
        "inflation",
        "energy",
        "tax_policy",
    ):

        if action == "increase":
            return "negative"

        if action == "decrease":
            return "positive"

    # Export growth and investment growth
    # are generally positive at the macro level.
    if event_type in (
        "trade",
        "investment",
    ):

        if action == "increase":
            return "positive"

        if action == "decrease":
            return "negative"

    # Market movement remains contextual.
    if event_type == "market_movement":

        if action == "increase":
            return "positive"

        if action == "decrease":
            return "negative"

    return "neutral"


# ============================================================
# BUILD EVENT
# ============================================================

def build_event(row):

    title = row["title"] or ""

    description = row["description"] or ""

    content = row["content"] or ""

    text = normalize(
        f"{title} {description} {content}"
    )

    event_type = detect_from_rules(
        text,
        EVENT_RULES
    )

    action = detect_from_rules(
        text,
        ACTION_RULES
    )

    sector = detect_from_rules(
        text,
        SECTOR_RULES
    )

    entity = detect_entity(text)

    importance = detect_importance(text)

    direction = detect_direction(
        event_type,
        action
    )

    return {

        "article_id": row["id"],

        "headline": title,

        "event_type": event_type,

        "action": action,

        "entity": entity,

        "sector": sector,

        "direction": direction,

        "importance": importance,

        "location": "Pakistan",

        "description": description,

    }


# ============================================================
# DATABASE HELPERS
# ============================================================

def get_columns(db, table):

    rows = db.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return [
        row[1]
        for row in rows
    ]


def find_column(
    columns,
    possible_names
):

    for name in possible_names:

        if name in columns:
            return name

    return None


# ============================================================
# INSERT EVENT
# ============================================================

def insert_event(
    db,
    event,
    columns
):

    mapping = {

        "article_id": [
            "article_id",
            "source_article_id",
            "article",
            "article_id_fk",
        ],

        "headline": [
            "headline",
            "title",
            "name",
            "event_title",
        ],

        "event_type": [
            "event_type",
            "type",
            "category",
        ],

        "action": [
            "action",
            "event_action",
        ],

        "entity": [
            "entity",
            "entity_name",
            "organization",
            "company",
        ],

        "sector": [
            "sector",
        ],

        "direction": [
            "direction",
            "impact_direction",
        ],

        "importance": [
            "importance",
            "importance_score",
            "priority",
        ],

        "location": [
            "location",
        ],

        "description": [
            "description",
            "summary",
            "details",
            "event_description",
        ],
    }

    insert_columns = []

    values = []

    for event_key, possible_names in mapping.items():

        actual_column = find_column(
            columns,
            possible_names
        )

        if actual_column:

            insert_columns.append(
                actual_column
            )

            values.append(
                event[event_key]
            )

    # --------------------------------------------------------
    # Handle common required fields that may not be in mapping
    # --------------------------------------------------------

    # If the table has a required headline, make absolutely
    # sure it gets populated.
    if (
        "headline" in columns
        and "headline" not in insert_columns
    ):

        insert_columns.append("headline")
        values.append(event["headline"])

    # If event_type exists and wasn't mapped.
    if (
        "event_type" in columns
        and "event_type" not in insert_columns
    ):

        insert_columns.append("event_type")
        values.append(event["event_type"])

    if not insert_columns:

        raise RuntimeError(
            "No compatible event columns found."
        )

    placeholders = ", ".join(
        ["?"] * len(values)
    )

    sql = f"""
        INSERT INTO events
        ({", ".join(insert_columns)})
        VALUES ({placeholders})
    """

    db.execute(
        sql,
        values
    )


# ============================================================
# DUPLICATE CHECK
# ============================================================

def event_already_exists(
    db,
    article_id,
    columns
):

    article_column = find_column(
        columns,
        [
            "article_id",
            "source_article_id",
            "article",
            "article_id_fk",
        ]
    )

    if article_column:

        row = db.execute(
            f"""
            SELECT 1
            FROM events
            WHERE {article_column} = ?
            LIMIT 1
            """,
            (article_id,),
        ).fetchone()

        return row is not None

    # If there is no article relationship column,
    # use headline as a secondary duplicate check.
    if "headline" in columns:

        row = db.execute(
            """
            SELECT 1
            FROM events
            WHERE headline = ?
            LIMIT 1
            """,
            (
                "PLACEHOLDER",
            ),
        ).fetchone()

        # No reliable article mapping exists,
        # so don't incorrectly skip events.
        return False

    return False


# ============================================================
# MAIN ENGINE
# ============================================================

def run_event_engine():

    db = sqlite3.connect(
        DATABASE_PATH
    )

    db.row_factory = sqlite3.Row

    print()
    print("=" * 70)
    print("ASNA EVENT EXTRACTION ENGINE")
    print("=" * 70)

    # --------------------------------------------------------
    # Verify tables
    # --------------------------------------------------------

    tables = [
        row[0]
        for row in db.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            """
        ).fetchall()
    ]

    if "events" not in tables:

        print(
            "[ERROR] events table does not exist."
        )

        db.close()
        return

    if "articles" not in tables:

        print(
            "[ERROR] articles table does not exist."
        )

        db.close()
        return

    # --------------------------------------------------------
    # Inspect events schema
    # --------------------------------------------------------

    event_columns = get_columns(
        db,
        "events"
    )

    print()
    print("EVENT TABLE COLUMNS")

    for column in event_columns:

        print(
            f"  - {column}"
        )

    # --------------------------------------------------------
    # Load classified articles
    # --------------------------------------------------------

    articles = db.execute(
        """
        SELECT
            id,
            title,
            description,
            content,
            category,
            subcategory
        FROM articles
        WHERE processed = 1
        ORDER BY id ASC
        """
    ).fetchall()

    print()
    print(
        f"Classified articles found: "
        f"{len(articles)}"
    )

    if not articles:

        print(
            "[INFO] No classified articles found."
        )

        db.close()
        return

    created = 0

    skipped = 0

    errors = 0

    event_counter = Counter()

    sector_counter = Counter()

    direction_counter = Counter()

    # --------------------------------------------------------
    # Process articles
    # --------------------------------------------------------

    for index, article in enumerate(
        articles,
        start=1
    ):

        if event_already_exists(
            db,
            article["id"],
            event_columns
        ):

            skipped += 1

            continue

        event = build_event(
            article
        )

        try:

            insert_event(
                db,
                event,
                event_columns
            )

            created += 1

            event_counter[
                event["event_type"]
            ] += 1

            sector_counter[
                event["sector"]
            ] += 1

            direction_counter[
                event["direction"]
            ] += 1

            print(
                f"[{index}/{len(articles)}] "
                f"{event['event_type']:22} | "
                f"{event['sector']:16} | "
                f"{event['direction']:20} | "
                f"Imp {event['importance']} | "
                f"{event['headline'][:55]}"
            )

        except Exception as error:

            errors += 1

            print(
                f"[ERROR] Article "
                f"{article['id']}: "
                f"{error}"
            )

    # --------------------------------------------------------
    # Commit
    # --------------------------------------------------------

    db.commit()

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("EVENT EXTRACTION COMPLETE")
    print("=" * 70)

    print(
        f"Events created:       {created}"
    )

    print(
        f"Already existing:     {skipped}"
    )

    print(
        f"Errors:               {errors}"
    )

    print()
    print("EVENT TYPES")

    if event_counter:

        for event_type, count in (
            event_counter.most_common()
        ):

            print(
                f"{event_type:30} {count}"
            )

    else:

        print("No new events.")

    print()
    print("SECTORS")

    if sector_counter:

        for sector, count in (
            sector_counter.most_common()
        ):

            print(
                f"{sector:30} {count}"
            )

    else:

        print("No new sectors.")

    print()
    print("DIRECTION")

    if direction_counter:

        for direction, count in (
            direction_counter.most_common()
        ):

            print(
                f"{direction:30} {count}"
            )

    print()
    print("=" * 70)

    db.close()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    run_event_engine()