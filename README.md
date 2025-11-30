# TCMB MCP

Production-ready MCP (Model Context Protocol) server for Turkish Central Bank (TCMB) exchange rates.

[![smithery badge](https://smithery.ai/badge/@ofurkanuygur/tcmb_mcp)](https://smithery.ai/server/@ofurkanuygur/tcmb_mcp)

## Features

- **Current Rates**: Get today's exchange rates from TCMB
- **Historical Rates**: Query rates for any date since 1996
- **Currency Conversion**: Convert between any currencies (including TRY)
- **Rate History**: Get rate history with statistics (min, max, avg, change %)
- **Multi-Currency Comparison**: Compare multiple currencies over time
- **Smart Caching**: SQLite-based cache with configurable TTL
- **Holiday Support**: Automatic fallback to previous business day
- **Turkish Holidays**: Includes all official and religious holidays

## Installation

### Using Smithery (Recommended)

Install directly via [Smithery](https://smithery.ai/server/@ofurkanuygur/tcmb_mcp):

```bash
npx -y @smithery/cli install @ofurkanuygur/tcmb_mcp --client claude
```

### Using uv (Local Development)

```bash
git clone https://github.com/ofurkanuygur/tcmb_mcp.git
cd tcmb_mcp
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e .
```

### Using pip

```bash
pip install tcmb-mcp
```

## Usage

### Claude Desktop Configuration

Add to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "tcmb": {
      "command": "python",
      "args": ["-m", "tcmb_mcp"],
      "env": {
        "TCMB_CACHE_ENABLED": "true",
        "TCMB_DEBUG": "false"
      }
    }
  }
}
```

### Running Manually

```bash
# stdio mode (default, for Claude Desktop)
python -m tcmb_mcp

# HTTP mode (for Smithery deployment)
MCP_TRANSPORT=http python -m tcmb_mcp
```

### Testing with MCP Inspector

```bash
npx @modelcontextprotocol/inspector python -m tcmb_mcp
```

## Available Tools

### 1. tcmb_get_current_rates

Get current exchange rates from TCMB.

```
Dolar ve Euro kurunu göster
→ tcmb_get_current_rates(currencies=["USD", "EUR"])
```

### 2. tcmb_get_historical_rates

Get exchange rates for a specific date.

```
15 Ocak 2024 kurlarını getir
→ tcmb_get_historical_rates(date="2024-01-15")
```

### 3. tcmb_list_currencies

List all available currencies.

```
Hangi para birimleri var?
→ tcmb_list_currencies()
```

### 4. tcmb_convert_currency

Convert between currencies.

```
1000 Dolar kaç TL?
→ tcmb_convert_currency(amount=1000, from_currency="USD", to_currency="TRY")
```

### 5. tcmb_get_rate_history

Get rate history with statistics.

```
Son 30 günde Dolar nasıl değişti?
→ tcmb_get_rate_history(currency="USD", start_date="2024-11-01", end_date="2024-11-30")
```

### 6. tcmb_compare_currencies

Compare multiple currencies.

```
Dolar, Euro ve Sterlin'i karşılaştır
→ tcmb_compare_currencies(target_currencies=["USD", "EUR", "GBP"])
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TCMB_CACHE_ENABLED` | `true` | Enable SQLite caching |
| `TCMB_CACHE_DB_PATH` | `~/.cache/tcmb-mcp/tcmb_cache.db` | Cache database path |
| `TCMB_CACHE_TTL_TODAY` | `3600` | Cache TTL for today (seconds) |
| `TCMB_CACHE_TTL_HISTORICAL` | `31536000` | Cache TTL for historical (seconds) |
| `TCMB_TIMEOUT` | `10` | API timeout (seconds) |
| `TCMB_MAX_RETRIES` | `3` | Maximum retry attempts |
| `TCMB_DEBUG` | `false` | Enable debug logging |
| `TCMB_LOG_LEVEL` | `INFO` | Log level |
| `MCP_TRANSPORT` | `stdio` | Transport mode (`stdio` or `http`) |
| `PORT` | `8080` | HTTP server port (when using HTTP transport) |

## Development

### Setup

```bash
git clone https://github.com/ofurkanuygur/tcmb_mcp.git
cd tcmb_mcp
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src/tcmb_mcp --cov-report=term-missing

# Unit tests only
pytest tests/unit/
```

### Code Quality

```bash
# Linting
ruff check src/

# Type checking
mypy src/
```

### Local HTTP Server Testing

```bash
# Start server in HTTP mode
MCP_TRANSPORT=http python -m tcmb_mcp

# Test with Smithery playground
npx -y @smithery/cli playground --port 8080
```

## Docker

### Build

```bash
docker build -t tcmb-mcp .
```

### Run

```bash
docker run -p 8080:8080 tcmb-mcp
```

## API Reference

### TCMB URL Format

- Today's rates: `https://www.tcmb.gov.tr/kurlar/today.xml`
- Historical: `https://www.tcmb.gov.tr/kurlar/YYYYMM/DDMMYYYY.xml`
  - Example: January 15, 2024 → `/kurlar/202401/15012024.xml`

### Rate Types

| Type | Turkish | Description |
|------|---------|-------------|
| `forex_buying` | Döviz Alış | Electronic transfer buying rate |
| `forex_selling` | Döviz Satış | Electronic transfer selling rate |
| `banknote_buying` | Efektif Alış | Cash buying rate |
| `banknote_selling` | Efektif Satış | Cash selling rate |

## Author

**Oktay Furkan Uygur**
- GitHub: [@ofurkanuygur](https://github.com/ofurkanuygur)

## Acknowledgments

- [TCMB](https://www.tcmb.gov.tr) for providing public exchange rate data
- [Anthropic](https://anthropic.com) for the MCP protocol
- [Smithery](https://smithery.ai) for MCP server hosting