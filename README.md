<div align="center">
  <h1>earnings-calendar</h1>
  <h4 align="center">
    Subscribe-ready ICS feeds for earnings.
  </h4>
  <p>Earnings dates published as ICS feeds you can subscribe to.</p>
</div>

> [!WARNING]
> This calendar is for planning purposes only. Do not use it for trading or investment decisions.

## ✨ What this is

A calendar with **quarterly earnings dates** published as ICS feeds you can subscribe to. Tickers are fully configurable — any symbol supported by [Finnhub](https://finnhub.io/) can be added.

### 📝 Example event

```
NVDA Q2 Earnings
─────────────────
Ticker: NVDA
Fiscal Qtr: 2
Estimate EPS: 1.0281
Est. Revenue: 46.98 B
Source: Finnhub
```

## 📥 Subscribe

> [!TIP]
> Subscribing with the link below keeps the calendar **updated automatically**, no re-imports needed.

```
https://raw.githubusercontent.com/bowencool/earnings-calendar/refs/heads/public/calendar.ics
```

**Apple Calendar** — Calendar → File → New Calendar Subscription… → paste the URL.

**Google Calendar** — Left sidebar → Other calendars → From URL → paste the URL.

**Outlook** — File → Account Settings → Internet Calendars → New… → paste the URL.

## 🚀 Install & Run

```bash
# Install from source
git clone https://github.com/bowencool/earnings-calendar.git
cd earnings-calendar
uv sync

# Run
uv run earnings-calendar --config .github/earnings-calendar.yaml earnings
```

## ⚙️ Configuration

Create a config file at `~/.config/earnings-calendar/config.yaml` (or pass `--config <path>`):

```yaml
earnings:
  tickers: ["AAPL", "MSFT", "GOOG", "NVDA"]   # any Finnhub-supported symbols
  api_key: <your API key>                       # or set TC_FINNHUB_API_KEY
  days_ahead: 20
  days_past: 10
  calendar:
    ics_path: "earnings.ics"
    name: "Earnings Calendar"
```

### Environment variables

| Variable | Description |
|---|---|
| `TC_FINNHUB_API_KEY` | Finnhub API key (overrides `api_key` in config) |
| `TC_STORAGE_DB_PATH` | Storage path, supports `file://` and `webdav://` (optional, defaults to `file://earnings_calendar.db`) |

> The WebDAV backend does not create directories, so the parent folder must already exist.
