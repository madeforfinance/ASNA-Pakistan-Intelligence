# ASNA Pakistan Intelligence - Next Stage

## 1. Keep the existing working modules

Do not replace these unless specifically instructed:

- news/collector.py
- news/event_engine.py
- news/impact_engine.py
- news/alert_engine.py
- news/discord_reporter.py

## 2. Replace/add these files

Add or replace:

- news/daily_digest.py
- news/market_intelligence.py
- news/weekly_digest.py
- news/system_health.py
- news/source_health.py
- news/trend_engine.py
- news/scheduler.py

## 3. Required environment

The existing `.env` must contain:

DISCORD_TOKEN=...
DISCORD_GUILD_ID=1551362175459663934

Optional:

INTELLIGENCE_DB=data/intelligence.db

## 4. Test in this order

Stop any running scheduler first.

### Test daily digest

python news/daily_digest.py

### Test market intelligence

python news/market_intelligence.py

### Test trends

python news/trend_engine.py

### Test source health

python news/source_health.py

### Test system health

python news/system_health.py

### Test weekly report

python news/weekly_digest.py

## 5. Start the complete system

python news/scheduler.py

Only one scheduler instance should be running.

## 6. Expected Discord structure

🧠 INTELLIGENCE
- daily-intelligence
- market-intelligence
- trend-intelligence
- weekly-intelligence
- finance-intelligence
- markets-intelligence
- business-intelligence
- economy-intelligence
- energy-intelligence
- trade-intelligence
- regulatory-intelligence
- technology-intelligence
- agriculture-intelligence
- banking-intelligence
- news-intelligence

⚙️ SYSTEM
- system-health
- source-health

🚨 ALERTS
- breaking-news
- high-impact
- important-updates
- news-updates

## 7. Current architecture

Hourly:
Collector -> Event Engine -> Impact Engine -> Alert Engine -> Reporter

Daily:
Daily Digest + Source Health + System Health

Every 6 hours:
Market Intelligence + Trend Intelligence

Weekly:
Weekly Intelligence

## 8. Important limitation

Market Intelligence currently analyzes market-related EVENTS already captured by the pipeline. It is not yet a live PSX price/ticker engine. A live market-data layer should be added separately rather than pretending news events are price data. Humanity has enough fake dashboards already.

## 9. Duplicate protection

Daily digest uses digest_runs.
Market intelligence uses market_reports.

The modules are designed as one-shot jobs and are called sequentially by scheduler.py. Do not manually run several Discord bot modules simultaneously.
