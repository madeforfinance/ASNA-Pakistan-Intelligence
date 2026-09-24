# ASNA Pakistan Intelligence - GitHub Deployment Pack

This pack adds GitHub Actions deployment without changing the Discord reporter's routing/functionality.

## IMPORTANT

The `news/` directory in this pack contains the next-stage modules supplied for the project. Your existing working modules must remain in the same project and are intentionally not replaced by this deployment pack:

- collector.py
- rss.py
- scraper.py
- classifier.py
- deduplicator.py
- event_engine.py
- impact_engine.py
- alert_engine.py
- discord_reporter.py
- news/sources/__init__.py

If those files already exist in your working project, keep them. Do not delete them.

## GitHub workflows

- `hourly-intelligence.yml`: collector -> event -> impact -> alerts -> existing Discord reporter
- `daily-intelligence.yml`: daily digest -> source health -> system health
- `weekly-intelligence.yml`: weekly digest -> trend engine

All workflows use the same concurrency group so the SQLite database is not modified by two workflows simultaneously.

## Secrets

Repository Settings -> Secrets and variables -> Actions:

- `DISCORD_TOKEN`
- `DISCORD_GUILD_ID` = `1551362175459663934`

Never commit `.env` or the Discord token.

## Database

`data/intelligence.db` is intentionally persisted by committing changes back to the repository. This is the simplest $0 deployment approach, but it means the database contents are visible if the repository is public. Do not put private information in it.

## Schedule

GitHub cron uses UTC:

- Hourly: minute 5 of every hour
- Daily: 15:00 UTC = 20:00 Pakistan Standard Time
- Weekly: Sunday 16:00 UTC = Sunday 21:00 Pakistan Standard Time

GitHub scheduled workflows can be delayed during periods of high load.

## Local testing

Run from the project root:

```powershell
python news/daily_digest.py
python news/market_intelligence.py
python news/trend_engine.py
python news/source_health.py
python news/system_health.py
python news/weekly_digest.py
python -m news.collector
python news/event_engine.py
python news/impact_engine.py
python news/alert_engine.py
python news/discord_reporter.py
```

Do not use `scheduler.py` in GitHub Actions. GitHub itself supplies the schedule.
