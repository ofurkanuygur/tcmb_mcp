"""MCP Server for TCMB exchange rates."""

import asyncio
import json
import os

from mcp.server import Server
from mcp.server.fastmcp import FastMCP
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool, ToolAnnotations

from tcmb_mcp.core.config import get_settings
from tcmb_mcp.core.container import cleanup, initialize
from tcmb_mcp.core.exceptions import TCMBError
from tcmb_mcp.core.logging import get_logger, setup_logging
from tcmb_mcp.tools import (
    compare_currencies,
    convert_currency,
    get_current_rates,
    get_historical_rates,
    get_rate_history,
    list_currencies,
)

# Initialize logging
settings = get_settings()
setup_logging(debug=settings.debug, log_level=settings.log_level)
logger = get_logger(__name__)

# Create FastMCP server for HTTP mode
mcp = FastMCP(
    name="tcmb-mcp",
    json_response=False,
    stateless_http=True,  # Smithery uses stateless
)

# Create standard Server for stdio mode
app = Server("tcmb-mcp")


# Tool annotations (MCP best practice)
TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,       # Veri değiştirmiyor
    destructiveHint=False,   # Zarar vermiyor
    idempotentHint=True,     # Aynı sonuç
    openWorldHint=True,      # Dış API çağırıyor
)


# Tool definitions with tcmb_ prefix (MCP naming convention)
TOOLS = [
    Tool(
        name="tcmb_get_current_rates",
        description="Güncel döviz kurlarını TCMB'den getirir.",
        inputSchema={
            "type": "object",
            "properties": {
                "currencies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Para birimi kodları (örn: ['USD', 'EUR']).",
                },
            },
        },
        annotations=TOOL_ANNOTATIONS,
    ),
    Tool(
        name="tcmb_get_historical_rates",
        description="Belirli bir tarih için geçmiş döviz kurlarını getirir.",
        inputSchema={
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Tarih (YYYY-MM-DD, DD.MM.YYYY veya 'dün')",
                },
                "currencies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filtrelenecek para birimi kodları",
                },
            },
            "required": ["date"],
        },
        annotations=TOOL_ANNOTATIONS,
    ),
    Tool(
        name="tcmb_list_currencies",
        description="TCMB'de mevcut tüm para birimlerini listeler.",
        inputSchema={
            "type": "object",
            "properties": {
                "include_rates": {
                    "type": "boolean",
                    "description": "Güncel kur bilgisi eklensin mi?",
                    "default": False,
                },
            },
        },
        annotations=TOOL_ANNOTATIONS,
    ),
    Tool(
        name="tcmb_convert_currency",
        description="Para birimlerini çevirir (TRY dahil).",
        inputSchema={
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "Çevrilecek miktar",
                },
                "from_currency": {
                    "type": "string",
                    "description": "Kaynak para birimi (örn: USD, EUR, TRY)",
                },
                "to_currency": {
                    "type": "string",
                    "description": "Hedef para birimi",
                },
                "rate_type": {
                    "type": "string",
                    "enum": ["buying", "selling"],
                    "description": "Kur tipi (alış veya satış)",
                    "default": "selling",
                },
            },
            "required": ["amount", "from_currency", "to_currency"],
        },
        annotations=TOOL_ANNOTATIONS,
    ),
    Tool(
        name="tcmb_get_rate_history",
        description="Para birimi kur geçmişi ve istatistikleri.",
        inputSchema={
            "type": "object",
            "properties": {
                "currency": {
                    "type": "string",
                    "description": "Para birimi kodu (örn: USD, EUR)",
                },
                "start_date": {
                    "type": "string",
                    "description": "Başlangıç tarihi (YYYY-MM-DD)",
                },
                "end_date": {
                    "type": "string",
                    "description": "Bitiş tarihi (YYYY-MM-DD)",
                },
                "rate_type": {
                    "type": "string",
                    "enum": ["buying", "selling"],
                    "description": "Kur tipi",
                    "default": "selling",
                },
            },
            "required": ["currency", "start_date", "end_date"],
        },
        annotations=TOOL_ANNOTATIONS,
    ),
    Tool(
        name="tcmb_compare_currencies",
        description="Birden fazla para birimini karşılaştırır.",
        inputSchema={
            "type": "object",
            "properties": {
                "target_currencies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Karşılaştırılacak para birimleri",
                },
                "base_currency": {
                    "type": "string",
                    "description": "Baz para birimi",
                    "default": "TRY",
                },
                "days": {
                    "type": "integer",
                    "description": "Geriye bakılacak gün sayısı",
                    "default": 30,
                },
            },
            "required": ["target_currencies"],
        },
        annotations=TOOL_ANNOTATIONS,
    ),
]


# Register tools for stdio server
@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return TOOLS


async def _call_tool_impl(name: str, arguments: dict) -> dict:
    """Common tool implementation."""
    if name == "tcmb_get_current_rates":
        return await get_current_rates(
            currencies=arguments.get("currencies"),
        )
    elif name == "tcmb_get_historical_rates":
        return await get_historical_rates(
            date_str=arguments["date"],
            currencies=arguments.get("currencies"),
        )
    elif name == "tcmb_list_currencies":
        return await list_currencies(
            include_rates=arguments.get("include_rates", False),
        )
    elif name == "tcmb_convert_currency":
        return await convert_currency(
            amount=arguments["amount"],
            from_currency=arguments["from_currency"],
            to_currency=arguments["to_currency"],
            rate_type=arguments.get("rate_type", "selling"),
        )
    elif name == "tcmb_get_rate_history":
        return await get_rate_history(
            currency=arguments["currency"],
            start_date=arguments["start_date"],
            end_date=arguments["end_date"],
            rate_type=arguments.get("rate_type", "selling"),
        )
    elif name == "tcmb_compare_currencies":
        return await compare_currencies(
            target_currencies=arguments["target_currencies"],
            base_currency=arguments.get("base_currency", "TRY"),
            days=arguments.get("days", 30),
        )
    else:
        return {"error": True, "message": f"Bilinmeyen tool: {name}"}


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Route tool calls to appropriate handlers (stdio mode)."""
    logger.info("tool_called", tool=name, arguments=arguments)

    try:
        result = await _call_tool_impl(name, arguments)
        result_text = json.dumps(result, ensure_ascii=False, indent=2, default=str)
        logger.info("tool_completed", tool=name)
        return [TextContent(type="text", text=result_text)]

    except TCMBError as e:
        logger.error("tool_error", tool=name, error=str(e))
        error_text = json.dumps(e.to_dict(), ensure_ascii=False, indent=2)
        return [TextContent(type="text", text=error_text)]

    except Exception as e:
        logger.exception("tool_unexpected_error", tool=name)
        error_result = {
            "error": True,
            "code": "INTERNAL_ERROR",
            "message": f"Beklenmeyen hata: {str(e)}",
        }
        return [TextContent(type="text", text=json.dumps(error_result, ensure_ascii=False))]


# Register tools for FastMCP (HTTP mode)
@mcp.tool()
async def tcmb_get_current_rates(currencies: list[str] | None = None) -> str:
    """Güncel döviz kurlarını TCMB'den getirir."""
    await initialize()
    result = await get_current_rates(currencies=currencies)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def tcmb_get_historical_rates(date: str, currencies: list[str] | None = None) -> str:
    """Belirli bir tarih için geçmiş döviz kurlarını getirir."""
    await initialize()
    result = await get_historical_rates(date_str=date, currencies=currencies)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def tcmb_list_currencies(include_rates: bool = False) -> str:
    """TCMB'de mevcut tüm para birimlerini listeler."""
    await initialize()
    result = await list_currencies(include_rates=include_rates)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def tcmb_convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
    rate_type: str = "selling"
) -> str:
    """Para birimlerini çevirir (TRY dahil)."""
    await initialize()
    result = await convert_currency(
        amount=amount,
        from_currency=from_currency,
        to_currency=to_currency,
        rate_type=rate_type,
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def tcmb_get_rate_history(
    currency: str,
    start_date: str,
    end_date: str,
    rate_type: str = "selling"
) -> str:
    """Para birimi kur geçmişi ve istatistikleri."""
    await initialize()
    result = await get_rate_history(
        currency=currency,
        start_date=start_date,
        end_date=end_date,
        rate_type=rate_type,
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def tcmb_compare_currencies(
    target_currencies: list[str],
    base_currency: str = "TRY",
    days: int = 30
) -> str:
    """Birden fazla para birimini karşılaştırır."""
    await initialize()
    result = await compare_currencies(
        target_currencies=target_currencies,
        base_currency=base_currency,
        days=days,
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


async def run_stdio_server() -> None:
    """Run the MCP server with stdio transport."""
    logger.info("server_starting", version="1.0.0", transport="stdio")

    try:
        await initialize()

        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options(),
            )

    except Exception:
        logger.exception("server_error")
        raise

    finally:
        await cleanup()
        logger.info("server_stopped")


def run_server() -> None:
    """Run the MCP server (auto-detect mode from environment)."""
    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()

    if transport in ("http", "sse", "streamable"):
        import uvicorn
        from starlette.middleware.cors import CORSMiddleware

        port = int(os.environ.get("PORT", "8080"))
        host = os.environ.get("HOST", "0.0.0.0")

        # Create streamable HTTP app with CORS
        http_app = mcp.streamable_http_app()
        http_app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["mcp-session-id", "mcp-protocol-version"],
            max_age=86400,
        )

        logger.info("server_starting", version="1.0.0", transport="http", port=port)
        uvicorn.run(http_app, host=host, port=port)
    else:
        asyncio.run(run_stdio_server())


if __name__ == "__main__":
    run_server()
