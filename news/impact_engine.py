import sqlite3
import re
from collections import Counter
from datetime import datetime


DATABASE_PATH = "data/intelligence.db"


# ============================================================
# IMPACT RULES
# ============================================================

IMPACT_RULES = {

    "energy_price_increase": {
        "keywords": [
            "petrol price",
            "petrol prices",
            "diesel price",
            "electricity tariff",
            "power tariff",
            "gas tariff",
            "oil price",
        ],
        "impact": {
            "business": "Higher operating and transportation costs may pressure business margins.",
            "consumer": "Higher household and transportation expenses may reduce purchasing power.",
            "economy": "Higher energy costs can contribute to inflationary pressure.",
            "market": "Energy-intensive companies may face margin pressure.",
        },
    },

    "energy_price_decrease": {
        "keywords": [
            "petrol price cut",
            "petrol prices reduced",
            "diesel price cut",
            "electricity tariff reduction",
            "gas tariff reduction",
            "oil price decline",
        ],
        "impact": {
            "business": "Lower energy and transportation costs may support operating margins.",
            "consumer": "Lower energy expenses may improve disposable income.",
            "economy": "Lower energy prices can reduce inflationary pressure.",
            "market": "Energy-intensive sectors may benefit from lower costs.",
        },
    },

    "interest_rate_increase": {
        "keywords": [
            "interest rate increased",
            "interest rate hike",
            "policy rate increased",
            "policy rate hike",
            "rate hike",
        ],
        "impact": {
            "business": "Higher borrowing costs may increase financing expenses and reduce investment incentives.",
            "consumer": "Loans and financing may become more expensive.",
            "economy": "Tighter financial conditions may reduce demand and investment.",
            "market": "Higher rates can affect equity valuations and borrowing-sensitive companies.",
            "banking": "Banks may experience changes in lending demand and interest margins.",
        },
    },

    "interest_rate_decrease": {
        "keywords": [
            "interest rate cut",
            "interest rate decreased",
            "policy rate cut",
            "policy rate decreased",
            "rate cut",
        ],
        "impact": {
            "business": "Lower borrowing costs may support investment and business expansion.",
            "consumer": "Financing costs may decline.",
            "economy": "Easier financial conditions may support economic activity.",
            "market": "Lower rates can support equity valuations and investment activity.",
            "banking": "Lower rates may affect lending demand and bank margins.",
        },
    },

    "inflation_increase": {
        "keywords": [
            "inflation increased",
            "inflation rises",
            "inflation rate increased",
            "cpi increased",
            "consumer prices increased",
        ],
        "impact": {
            "business": "Input and operating costs may rise.",
            "consumer": "Purchasing power may decline as prices rise.",
            "economy": "Persistent inflation can affect consumption and investment decisions.",
            "market": "Inflation expectations can influence interest rates and asset valuations.",
        },
    },

    "inflation_decrease": {
        "keywords": [
            "inflation decreased",
            "inflation falls",
            "inflation rate decreased",
            "cpi decreased",
            "inflation eases",
        ],
        "impact": {
            "business": "Lower inflation may improve cost visibility.",
            "consumer": "Reduced price pressure can support purchasing power.",
            "economy": "Lower inflation can create room for monetary easing.",
            "market": "Lower inflation expectations may support investment.",
        },
    },

    "tax_increase": {
        "keywords": [
            "tax rate increased",
            "tax increase",
            "tax hike",
            "sales tax increased",
            "income tax increased",
            "withholding tax increased",
        ],
        "impact": {
            "business": "Higher taxes may increase compliance costs and reduce after-tax profitability.",
            "consumer": "Some tax increases may raise prices or reduce disposable income.",
            "economy": "Higher taxation can affect consumption and investment.",
            "government": "Government revenue may increase depending on compliance and the tax base.",
            "market": "Affected companies may experience earnings pressure.",
        },
    },

    "tax_reduction": {
        "keywords": [
            "tax cut",
            "tax reduction",
            "tax rate reduced",
            "sales tax reduced",
            "income tax reduced",
        ],
        "impact": {
            "business": "Lower taxes may improve after-tax profitability and investment incentives.",
            "consumer": "Tax reductions may improve disposable income or reduce prices.",
            "economy": "Lower taxes can support consumption or investment depending on the measure.",
            "government": "Government revenue may decline initially.",
            "market": "Affected companies may benefit from improved earnings expectations.",
        },
    },

    "exports_increase": {
        "keywords": [
            "exports increased",
            "export growth",
            "exports rise",
            "exports grew",
            "export earnings increased",
        ],
        "impact": {
            "business": "Higher export demand can support production and exporter revenues.",
            "currency": "Higher export receipts can support foreign-exchange inflows.",
            "economy": "Export growth can contribute to economic activity.",
            "employment": "Export-oriented sectors may experience stronger demand for labor.",
        },
    },

    "exports_decrease": {
        "keywords": [
            "exports decreased",
            "exports declined",
            "exports fell",
            "export decline",
        ],
        "impact": {
            "business": "Export-oriented companies may face weaker revenues.",
            "currency": "Lower export receipts can reduce foreign-exchange inflows.",
            "economy": "Weak export performance may weigh on external-sector activity.",
        },
    },

    "imports_increase": {
        "keywords": [
            "imports increased",
            "imports rise",
            "imports grew",
            "import bill increased",
        ],
        "impact": {
            "business": "Import-dependent businesses may gain access to inputs but face higher foreign-exchange requirements.",
            "currency": "Higher imports can increase demand for foreign currency.",
            "economy": "A larger import bill can affect the trade balance.",
        },
    },

    "investment_increase": {
        "keywords": [
            "investment increased",
            "investment rises",
            "investment growth",
            "foreign investment increased",
            "fdi increased",
            "new investment",
        ],
        "impact": {
            "business": "Additional investment can expand productive capacity and competition.",
            "employment": "New projects may create employment opportunities.",
            "economy": "Investment can support capital formation and economic activity.",
            "market": "Investment announcements may affect related companies and sectors.",
        },
    },

    "market_rise": {
        "keywords": [
            "psx gained",
            "psx rises",
            "psx rose",
            "stocks gained",
            "stock market gained",
            "kse-100 gained",
            "kse 100 gained",
        ],
        "impact": {
            "investor": "Higher equity prices may improve portfolio valuations.",
            "business": "Improved market sentiment can support equity financing conditions.",
            "market": "Positive market momentum may reflect stronger investor sentiment.",
        },
    },

    "market_decline": {
        "keywords": [
            "psx fell",
            "psx declined",
            "stocks fell",
            "stock market fell",
            "kse-100 fell",
            "kse 100 fell",
            "market decline",
        ],
        "impact": {
            "investor": "Portfolio valuations may decline.",
            "business": "Weak market sentiment can affect financing and investor confidence.",
            "market": "A market decline may indicate increased risk aversion or sector-specific pressure.",
        },
    },

    "imf_development": {
        "keywords": [
            "imf",
            "international monetary fund",
            "imf programme",
            "imf program",
            "imf tranche",
            "staff level agreement",
        ],
        "impact": {
            "government": "IMF-related developments can affect fiscal and economic policy.",
            "currency": "Programme developments can influence foreign-exchange expectations.",
            "business": "Associated reforms may affect taxation, energy pricing and regulation.",
            "market": "Investors may react to changes in external financing and reform expectations.",
        },
    },

    "corporate_profit": {
        "keywords": [
            "profit increased",
            "profit rises",
            "profit grew",
            "earnings increased",
            "revenue increased",
        ],
        "impact": {
            "business": "Improved earnings may strengthen the company's financial position.",
            "investor": "Stronger earnings may affect investor expectations.",
            "market": "Results may influence valuations and sector sentiment.",
        },
    },

    "corporate_loss": {
        "keywords": [
            "loss increased",
            "loss widened",
            "profit declined",
            "earnings declined",
            "revenue declined",
        ],
        "impact": {
            "business": "Weaker financial performance may pressure profitability and cash flow.",
            "investor": "Investors may reassess earnings expectations.",
            "market": "Results may indicate weaker demand or sector-specific pressure.",
        },
    },
}


# ============================================================
# FALLBACK
# ============================================================

GENERIC_IMPACTS = {
    "business": "The event may affect operating costs, revenues, investment or business confidence.",
    "consumer": "The event may affect household costs, purchasing power or access to goods and services.",
    "economy": "The event may have broader implications for economic activity and financial conditions.",
    "market": "The event may influence investor expectations and market sentiment.",
}


# ============================================================
# DATABASE SETUP
# ============================================================

def ensure_analysis_table(db):

    db.execute("""
        CREATE TABLE IF NOT EXISTS analyses (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            event_id INTEGER NOT NULL,

            summary TEXT,

            business_impact TEXT,

            consumer_impact TEXT,

            economic_impact TEXT,

            market_impact TEXT,

            government_impact TEXT,

            investor_impact TEXT,

            banking_impact TEXT,

            currency_impact TEXT,

            employment_impact TEXT,

            sector_impact TEXT,

            direction TEXT,

            importance INTEGER DEFAULT 1,

            confidence REAL DEFAULT 0.70,

            analysis_type TEXT DEFAULT 'rule_based',

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (event_id)
                REFERENCES events(id)
        )
    """)

    db.commit()

    print("[SYSTEM] Analyses table verified.")


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


def row_text(row):

    values = []

    for key in row.keys():

        value = row[key]

        if value is not None:
            values.append(str(value))

    return normalize(
        " ".join(values)
    )


# ============================================================
# FIND IMPACT RULE
# ============================================================

def find_impact_rule(
    text,
    event_type
):

    scores = Counter()

    for rule_name, rule in IMPACT_RULES.items():

        for keyword in rule["keywords"]:

            keyword = keyword.lower()

            if keyword in text:

                scores[rule_name] += max(
                    1,
                    len(keyword.split())
                )

    # Give the event's own type extra weight.
    event_mapping = {

        "energy": [
            "energy_price_increase",
            "energy_price_decrease",
        ],

        "monetary_policy": [
            "interest_rate_increase",
            "interest_rate_decrease",
        ],

        "inflation": [
            "inflation_increase",
            "inflation_decrease",
        ],

        "tax_policy": [
            "tax_increase",
            "tax_reduction",
        ],

        "trade": [
            "exports_increase",
            "exports_decrease",
            "imports_increase",
        ],

        "investment": [
            "investment_increase",
        ],

        "market_movement": [
            "market_rise",
            "market_decline",
        ],

        "imf": [
            "imf_development",
        ],

        "corporate_action": [
            "corporate_profit",
            "corporate_loss",
        ],
    }

    for candidate in event_mapping.get(
        event_type,
        []
    ):

        if candidate in scores:
            scores[candidate] += 5

    if not scores:
        return None

    return scores.most_common(1)[0][0]


# ============================================================
# DETECT DIRECTION
# ============================================================

def detect_direction(
    text,
    event_type
):

    positive_terms = [
        "increased",
        "increase",
        "growth",
        "grew",
        "gained",
        "rose",
        "rises",
        "approved",
        "agreement",
        "investment",
        "export growth",
    ]

    negative_terms = [
        "declined",
        "decline",
        "decreased",
        "decrease",
        "fell",
        "fall",
        "loss",
        "crisis",
        "hike",
        "inflation",
        "price increase",
    ]

    positive = sum(
        1
        for term in positive_terms
        if term in text
    )

    negative = sum(
        1
        for term in negative_terms
        if term in text
    )

    if event_type in (
        "energy",
        "inflation",
        "tax_policy",
    ):

        if "increase" in text or "increased" in text:
            return "negative"

        if "decrease" in text or "decreased" in text:
            return "positive"

    if positive > negative:
        return "positive"

    if negative > positive:
        return "negative"

    return "neutral"


# ============================================================
# IMPORTANCE
# ============================================================

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
        for term in high_terms
        if term in text
    )

    medium = sum(
        1
        for term in medium_terms
        if term in text
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


# ============================================================
# BUILD ANALYSIS
# ============================================================

def build_analysis(event):

    text = row_text(event)

    event_type = (
        event["event_type"]
        if "event_type" in event.keys()
        and event["event_type"]
        else "general"
    )

    rule_name = find_impact_rule(
        text,
        event_type
    )

    if rule_name:

        impacts = dict(
            IMPACT_RULES[rule_name]["impact"]
        )

    else:

        impacts = dict(
            GENERIC_IMPACTS
        )

    direction = detect_direction(
        text,
        event_type
    )

    importance = detect_importance(
        text
    )

    summary = (
        f"This event concerns "
        f"{event_type.replace('_', ' ')}. "
        f"The rule-based assessment indicates "
        f"a {direction} potential direction "
        f"for the directly affected areas. "
        f"Actual impact depends on the scale, "
        f"duration and implementation of the event."
    )

    return {

        "event_id": event["id"],

        "summary": summary,

        "business_impact":
            impacts.get(
                "business",
                ""
            ),

        "consumer_impact":
            impacts.get(
                "consumer",
                ""
            ),

        "economic_impact":
            impacts.get(
                "economy",
                ""
            ),

        "market_impact":
            impacts.get(
                "market",
                ""
            ),

        "government_impact":
            impacts.get(
                "government",
                ""
            ),

        "investor_impact":
            impacts.get(
                "investor",
                ""
            ),

        "banking_impact":
            impacts.get(
                "banking",
                ""
            ),

        "currency_impact":
            impacts.get(
                "currency",
                ""
            ),

        "employment_impact":
            impacts.get(
                "employment",
                ""
            ),

        "sector_impact":
            impacts.get(
                "sector",
                ""
            ),

        "direction":
            direction,

        "importance":
            importance,

        "confidence":
            0.70,

    }


# ============================================================
# DUPLICATE CHECK
# ============================================================

def analysis_exists(
    db,
    event_id
):

    row = db.execute(
        """
        SELECT id
        FROM analyses
        WHERE event_id = ?
        LIMIT 1
        """,
        (event_id,)
    ).fetchone()

    return row is not None


# ============================================================
# INSERT ANALYSIS
# ============================================================

def save_analysis(
    db,
    analysis
):

    db.execute(
        """
        INSERT INTO analyses (

            event_id,

            summary,

            business_impact,

            consumer_impact,

            economic_impact,

            market_impact,

            government_impact,

            investor_impact,

            banking_impact,

            currency_impact,

            employment_impact,

            sector_impact,

            direction,

            importance,

            confidence,

            analysis_type

        )

        VALUES (

            ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?

        )
        """,
        (

            analysis["event_id"],

            analysis["summary"],

            analysis["business_impact"],

            analysis["consumer_impact"],

            analysis["economic_impact"],

            analysis["market_impact"],

            analysis["government_impact"],

            analysis["investor_impact"],

            analysis["banking_impact"],

            analysis["currency_impact"],

            analysis["employment_impact"],

            analysis["sector_impact"],

            analysis["direction"],

            analysis["importance"],

            analysis["confidence"],

            "rule_based",

        )
    )


# ============================================================
# MAIN
# ============================================================

def run_impact_engine():

    db = sqlite3.connect(
        DATABASE_PATH
    )

    db.row_factory = sqlite3.Row

    print()
    print("=" * 70)
    print("ASNA IMPACT ANALYSIS ENGINE")
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
            "[ACTION] Run the Event Extraction Engine first:"
        )

        print(
            "python news/event_engine.py"
        )

        db.close()
        return

    # --------------------------------------------------------
    # Create analyses table
    # --------------------------------------------------------

    ensure_analysis_table(
        db
    )

    # --------------------------------------------------------
    # Load events
    # --------------------------------------------------------

    events = db.execute(
        """
        SELECT *
        FROM events
        ORDER BY id ASC
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

        print(
            "[ACTION] Run:"
        )

        print(
            "python news/event_engine.py"
        )

        db.close()
        return

    created = 0

    skipped = 0

    errors = 0

    type_counter = Counter()

    direction_counter = Counter()

    importance_counter = Counter()

    # --------------------------------------------------------
    # Process events
    # --------------------------------------------------------

    for index, event in enumerate(
        events,
        start=1
    ):

        if analysis_exists(
            db,
            event["id"]
        ):

            skipped += 1

            continue

        try:

            analysis = build_analysis(
                event
            )

            save_analysis(
                db,
                analysis
            )

            created += 1

            event_type = (
                event["event_type"]
                if "event_type" in event.keys()
                and event["event_type"]
                else "general"
            )

            type_counter[
                event_type
            ] += 1

            direction_counter[
                analysis["direction"]
            ] += 1

            importance_counter[
                analysis["importance"]
            ] += 1

            headline = ""

            if "headline" in event.keys():

                headline = (
                    event["headline"]
                    or ""
                )

            print(
                f"[{index}/{len(events)}] "
                f"{event_type:22} | "
                f"{analysis['direction']:9} | "
                f"Importance {analysis['importance']} | "
                f"{headline[:55]}"
            )

        except Exception as error:

            errors += 1

            print(
                f"[ERROR] Event "
                f"{event['id']}: "
                f"{error}"
            )

    db.commit()

    # --------------------------------------------------------
    # Final report
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("IMPACT ANALYSIS COMPLETE")
    print("=" * 70)

    print(
        f"Analyses created:     {created}"
    )

    print(
        f"Already existing:     {skipped}"
    )

    print(
        f"Errors:               {errors}"
    )

    print()
    print("EVENT TYPES ANALYZED")

    for event_type, count in (
        type_counter.most_common()
    ):

        print(
            f"{event_type:30} {count}"
        )

    print()
    print("IMPACT DIRECTIONS")

    for direction, count in (
        direction_counter.most_common()
    ):

        print(
            f"{direction:30} {count}"
        )

    print()
    print("IMPORTANCE DISTRIBUTION")

    for importance, count in sorted(
        importance_counter.items()
    ):

        print(
            f"Level {importance}: {count}"
        )

    print()
    print(
        "Database table: analyses"
    )

    print(
        f"Completed at: "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    print("=" * 70)

    db.close()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    run_impact_engine()