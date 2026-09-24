import re
import sqlite3
from collections import Counter

DATABASE_PATH = "data/intelligence.db"


# ============================================================
# CATEGORY DEFINITIONS
# ============================================================

CATEGORY_RULES = {

    "business": {
        "keywords": [
            "business",
            "company",
            "corporate",
            "enterprise",
            "startup",
            "merger",
            "acquisition",
            "ceo",
            "profit",
            "revenue",
            "sales",
            "industry",
            "industrial",
            "manufacturing",
            "factory",
            "firm",
        ]
    },

    "finance": {
        "keywords": [
            "finance",
            "financial",
            "bank",
            "banking",
            "loan",
            "credit",
            "deposit",
            "lending",
            "interest rate",
            "investment",
            "investor",
            "fund",
            "bond",
            "debt",
            "capital",
        ]
    },

    "economy": {
        "keywords": [
            "economy",
            "economic",
            "gdp",
            "inflation",
            "deflation",
            "growth",
            "recession",
            "employment",
            "unemployment",
            "consumer price",
            "cpi",
            "purchasing power",
            "economic growth",
        ]
    },

    "tax": {
        "keywords": [
            "tax",
            "taxes",
            "taxation",
            "fbr",
            "income tax",
            "sales tax",
            "withholding tax",
            "customs duty",
            "duty",
            "fiscal",
            "revenue collection",
            "taxpayer",
        ]
    },

    "trade": {
        "keywords": [
            "export",
            "exports",
            "import",
            "imports",
            "trade",
            "trade deficit",
            "trade surplus",
            "customs",
            "shipment",
            "shipping",
            "commerce",
            "international trade",
            "tariff",
        ]
    },

    "markets": {
        "keywords": [
            "psx",
            "stock exchange",
            "stocks",
            "shares",
            "share price",
            "kse",
            "index",
            "kse-100",
            "kse 100",
            "equity",
            "market capitalization",
            "trading session",
            "bullish",
            "bearish",
        ]
    },

    "energy": {
        "keywords": [
            "energy",
            "electricity",
            "power",
            "gas",
            "oil",
            "petrol",
            "diesel",
            "lng",
            "lpg",
            "nepra",
            "ogra",
            "refinery",
            "fuel",
            "tariff",
            "power generation",
        ]
    },

    "technology": {
        "keywords": [
            "technology",
            "tech",
            "software",
            "artificial intelligence",
            "ai",
            "digital",
            "fintech",
            "cybersecurity",
            "data",
            "internet",
            "telecom",
            "5g",
            "startup",
        ]
    },

    "government": {
        "keywords": [
            "government",
            "ministry",
            "cabinet",
            "prime minister",
            "federal government",
            "policy",
            "regulation",
            "regulator",
            "notification",
            "ordinance",
            "legislation",
            "parliament",
        ]
    },

    "current_affairs": {
        "keywords": [
            "pakistan",
            "politics",
            "political",
            "election",
            "assembly",
            "senate",
            "court",
            "supreme court",
            "high court",
            "security",
            "police",
            "protest",
            "minister",
        ]
    },
}


# ============================================================
# SUBCATEGORIES
# ============================================================

SUBCATEGORY_RULES = {

    "inflation": [
        "inflation",
        "cpi",
        "consumer price",
        "price hike",
        "prices increased",
    ],

    "interest_rates": [
        "interest rate",
        "policy rate",
        "monetary policy",
        "sbp rate",
    ],

    "imf": [
        "imf",
        "international monetary fund",
        "standby arrangement",
        "extended fund facility",
        "efp",
    ],

    "tax_policy": [
        "tax",
        "fbr",
        "income tax",
        "sales tax",
        "withholding tax",
        "tax collection",
    ],

    "monetary_policy": [
        "sbp",
        "monetary policy",
        "policy rate",
        "interest rate",
    ],

    "fiscal_policy": [
        "fiscal",
        "budget",
        "government spending",
        "public expenditure",
        "revenue target",
    ],

    "trade_policy": [
        "trade",
        "export",
        "import",
        "tariff",
        "customs",
    ],

    "psx": [
        "psx",
        "kse-100",
        "kse 100",
        "stock exchange",
        "shares",
        "stocks",
    ],

    "banking": [
        "bank",
        "banking",
        "deposit",
        "loan",
        "credit",
        "lending",
    ],

    "energy_policy": [
        "nepra",
        "ogra",
        "electricity tariff",
        "gas tariff",
        "power tariff",
        "energy policy",
    ],

    "oil_and_gas": [
        "oil",
        "gas",
        "petrol",
        "diesel",
        "lng",
        "lpg",
        "refinery",
    ],

    "corporate": [
        "company",
        "corporate",
        "merger",
        "acquisition",
        "ceo",
        "profit",
        "revenue",
    ],

    "exports": [
        "export",
        "exports",
        "exporters",
        "export growth",
    ],

    "imports": [
        "import",
        "imports",
        "importers",
    ],

    "investment": [
        "investment",
        "investor",
        "foreign investment",
        "fdi",
        "fund",
    ],
}


# ============================================================
# IMPORTANCE
# ============================================================

HIGH_IMPORTANCE_TERMS = [
    "imf",
    "default",
    "emergency",
    "crisis",
    "policy rate",
    "interest rate",
    "budget",
    "tax",
    "fbr",
    "sbp",
    "devaluation",
    "rupee",
    "inflation",
    "petrol price",
    "electricity tariff",
    "gas price",
    "psx crash",
    "market crash",
    "sanctions",
    "major agreement",
]

MEDIUM_IMPORTANCE_TERMS = [
    "investment",
    "exports",
    "imports",
    "profit",
    "revenue",
    "banking",
    "loan",
    "energy",
    "trade",
    "stock market",
]


# ============================================================
# TEXT PROCESSING
# ============================================================

def normalize_text(text):

    if not text:
        return ""

    text = str(text).lower()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def article_text(row):

    title = row["title"] or ""
    description = row["description"] or ""
    content = row["content"] or ""

    return normalize_text(
        f"{title} {description} {content}"
    )


# ============================================================
# CATEGORY DETECTION
# ============================================================

def detect_category(text):

    scores = Counter()

    for category, data in CATEGORY_RULES.items():

        for keyword in data["keywords"]:

            if keyword.lower() in text:

                # Longer phrases receive more weight
                weight = max(
                    1,
                    len(keyword.split())
                )

                scores[category] += weight

    if not scores:

        return "general"

    return scores.most_common(1)[0][0]


# ============================================================
# SUBCATEGORY DETECTION
# ============================================================

def detect_subcategory(text):

    scores = Counter()

    for subcategory, keywords in SUBCATEGORY_RULES.items():

        for keyword in keywords:

            if keyword.lower() in text:

                weight = max(
                    1,
                    len(keyword.split())
                )

                scores[subcategory] += weight

    if not scores:

        return "general"

    return scores.most_common(1)[0][0]


# ============================================================
# IMPORTANCE
# ============================================================

def calculate_importance(text):

    high_score = 0
    medium_score = 0

    for keyword in HIGH_IMPORTANCE_TERMS:

        if keyword.lower() in text:
            high_score += 1

    for keyword in MEDIUM_IMPORTANCE_TERMS:

        if keyword.lower() in text:
            medium_score += 1

    if high_score >= 2:
        return 5

    if high_score == 1:
        return 4

    if medium_score >= 2:
        return 3

    if medium_score == 1:
        return 2

    return 1


# ============================================================
# CLASSIFY ARTICLE
# ============================================================

def classify_article(row):

    text = article_text(row)

    category = detect_category(text)

    subcategory = detect_subcategory(text)

    importance = calculate_importance(text)

    return {
        "category": category,
        "subcategory": subcategory,
        "importance": importance,
    }


# ============================================================
# DATABASE CLASSIFICATION
# ============================================================

def classify_database():

    db = sqlite3.connect(
        DATABASE_PATH
    )

    db.row_factory = sqlite3.Row

    print()
    print("=" * 70)
    print("ASNA NEWS CLASSIFICATION ENGINE")
    print("=" * 70)

    rows = db.execute(
        """
        SELECT
            id,
            title,
            description,
            content,
            category,
            subcategory,
            processed
        FROM articles
        WHERE processed = 0
        ORDER BY id ASC
        """
    ).fetchall()

    print(
        f"Unprocessed articles: {len(rows)}"
    )

    processed_count = 0

    for row in rows:

        result = classify_article(row)

        db.execute(
            """
            UPDATE articles
            SET
                category = ?,
                subcategory = ?,
                processed = 1
            WHERE id = ?
            """,
            (
                result["category"],
                result["subcategory"],
                row["id"],
            ),
        )

        processed_count += 1

        print(
            f"[{processed_count}/{len(rows)}] "
            f"{result['category']:18} | "
            f"{result['subcategory']:20} | "
            f"Importance {result['importance']} | "
            f"{row['title'][:70]}"
        )

    db.commit()

    # Summary
    print()
    print("=" * 70)
    print("CLASSIFICATION COMPLETE")
    print("=" * 70)

    categories = db.execute(
        """
        SELECT category, COUNT(*)
        FROM articles
        GROUP BY category
        ORDER BY COUNT(*) DESC
        """
    ).fetchall()

    print("\nCATEGORY DISTRIBUTION")

    for category, count in categories:

        print(
            f"{category:25} {count}"
        )

    subcategories = db.execute(
        """
        SELECT subcategory, COUNT(*)
        FROM articles
        GROUP BY subcategory
        ORDER BY COUNT(*) DESC
        LIMIT 20
        """
    ).fetchall()

    print("\nTOP SUBCATEGORIES")

    for subcategory, count in subcategories:

        print(
            f"{subcategory:25} {count}"
        )

    print()
    print(
        f"Articles classified: {processed_count}"
    )

    print("=" * 70)

    db.close()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    classify_database()