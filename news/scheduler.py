import os
import subprocess
import sys
import time
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_module(label, command):
    print("\n" + "=" * 70)
    print(f"[RUNNING] {label}")
    print("=" * 70)

    try:
        result = subprocess.run(
            command,
            cwd=BASE,
            check=False,
        )

        if result.returncode == 0:
            print(f"[SUCCESS] {label}")
            return True

        print(f"[FAILED] {label} | exit code={result.returncode}")
        return False

    except Exception as exc:
        print(f"[ERROR] {label}: {exc}")
        return False


def run_hourly_pipeline():
    steps = [
        ("Collector", [sys.executable, "-m", "news.collector"]),
        ("Event Engine", [sys.executable, "news/event_engine.py"]),
        ("Impact Engine", [sys.executable, "news/impact_engine.py"]),
        ("Alert Engine", [sys.executable, "news/alert_engine.py"]),
        ("Discord Reporter", [sys.executable, "news/discord_reporter.py"]),
    ]

    results = []

    for label, command in steps:
        ok = run_module(label, command)
        results.append((label, ok))

        # Downstream modules need collector data.
        if label == "Collector" and not ok:
            print("[PIPELINE] Collector failed. Skipping downstream modules.")
            break

    return results


def run_daily_digest():
    return run_module(
        "Daily Intelligence Digest",
        [sys.executable, "news/daily_digest.py"],
    )


def run_market_intelligence():
    return run_module(
        "Market Intelligence",
        [sys.executable, "news/market_intelligence.py"],
    )


def run_trends():
    return run_module(
        "Trend Intelligence",
        [sys.executable, "news/trend_engine.py"],
    )


def run_source_health():
    return run_module(
        "Source Health",
        [sys.executable, "news/source_health.py"],
    )


def run_system_health():
    return run_module(
        "System Health",
        [sys.executable, "news/system_health.py"],
    )


def run_weekly_digest():
    return run_module(
        "Weekly Intelligence",
        [sys.executable, "news/weekly_digest.py"],
    )


def main():
    print("=" * 70)
    print("ASNA PAKISTAN INTELLIGENCE - MASTER SCHEDULER")
    print("=" * 70)

    last_daily = None
    last_market = None
    last_trend = None
    last_source_health = None
    last_system_health = None
    last_weekly = None

    # Run the core pipeline immediately.
    run_hourly_pipeline()

    while True:
        now = datetime.now()
        today = now.date()

        # Daily digest at 20:00 local machine time.
        if now.hour >= 20 and last_daily != today:
            run_daily_digest()
            last_daily = today

        # Market intelligence every 6 hours.
        market_bucket = (today, now.hour // 6)
        if last_market != market_bucket:
            run_market_intelligence()
            last_market = market_bucket

        # Trends every 6 hours.
        trend_bucket = (today, now.hour // 6)
        if last_trend != trend_bucket:
            run_trends()
            last_trend = trend_bucket

        # Source health once per day.
        if last_source_health != today and now.hour >= 9:
            run_source_health()
            last_source_health = today

        # System health once per day.
        if last_system_health != today and now.hour >= 9:
            run_system_health()
            last_system_health = today

        # Weekly digest Sunday at/after 20:30.
        weekly_key = today
        if now.weekday() == 6 and now.hour >= 20 and now.minute >= 30:
            if last_weekly != weekly_key:
                run_weekly_digest()
                last_weekly = weekly_key

        print(
            f"\n[NEXT] Core intelligence cycle in 60 minutes. "
            f"Current time: {now:%Y-%m-%d %H:%M:%S}"
        )

        for remaining in range(60, 0, -1):
            time.sleep(60)

        print("\n[HOURLY] Starting intelligence cycle...")
        run_hourly_pipeline()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[STOPPED] ASNA Intelligence Scheduler stopped.")
