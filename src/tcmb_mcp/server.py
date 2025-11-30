"""MCP Server for TCMB exchange rates."""

import asyncio
import os

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route
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

# Create MCP server
app = Server("tcmb-mcp-pro")


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


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """
    Route tool calls to appropriate handlers.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        List of TextContent with results
    """
    logger.info("tool_called", tool=name, arguments=arguments)

    try:
        result: dict

        if name == "tcmb_get_current_rates":
            result = await get_current_rates(
                currencies=arguments.get("currencies"),
            )

        elif name == "tcmb_get_historical_rates":
            result = await get_historical_rates(
                date_str=arguments["date"],
                currencies=arguments.get("currencies"),
            )

        elif name == "tcmb_list_currencies":
            result = await list_currencies(
                include_rates=arguments.get("include_rates", False),
            )

        elif name == "tcmb_convert_currency":
            result = await convert_currency(
                amount=arguments["amount"],
                from_currency=arguments["from_currency"],
                to_currency=arguments["to_currency"],
                rate_type=arguments.get("rate_type", "selling"),
            )

        elif name == "tcmb_get_rate_history":
            result = await get_rate_history(
                currency=arguments["currency"],
                start_date=arguments["start_date"],
                end_date=arguments["end_date"],
                rate_type=arguments.get("rate_type", "selling"),
            )

        elif name == "tcmb_compare_currencies":
            result = await compare_currencies(
                target_currencies=arguments["target_currencies"],
                base_currency=arguments.get("base_currency", "TRY"),
                days=arguments.get("days", 30),
            )

        else:
            result = {"error": True, "message": f"Bilinmeyen tool: {name}"}

        # Convert result to JSON string
        import json
        result_text = json.dumps(result, ensure_ascii=False, indent=2, default=str)

        logger.info("tool_completed", tool=name)
        return [TextContent(type="text", text=result_text)]

    except TCMBError as e:
        logger.error("tool_error", tool=name, error=str(e))
        import json
        error_text = json.dumps(e.to_dict(), ensure_ascii=False, indent=2)
        return [TextContent(type="text", text=error_text)]

    except Exception as e:
        logger.exception("tool_unexpected_error", tool=name)
        import json
        error_result = {
            "error": True,
            "code": "INTERNAL_ERROR",
            "message": f"Beklenmeyen hata: {str(e)}",
        }
        return [TextContent(type="text", text=json.dumps(error_result, ensure_ascii=False))]


async def run_stdio_server() -> None:
    """Run the MCP server with stdio transport."""
    logger.info("server_starting", version="1.0.0", transport="stdio")

    try:
        # Initialize services
        await initialize()

        # Run server
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
        # Cleanup
        await cleanup()
        logger.info("server_stopped")


def create_sse_app() -> Starlette:
    """Create Starlette app with SSE transport for HTTP mode."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await app.run(
                streams[0],
                streams[1],
                app.create_initialization_options(),
            )

    async def handle_messages(request):
        await sse.handle_post_message(request.scope, request.receive, request._send)

    async def on_startup():
        await initialize()
        logger.info("server_starting", version="1.0.0", transport="sse")

    async def on_shutdown():
        await cleanup()
        logger.info("server_stopped")

    return Starlette(
        debug=settings.debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/messages/", endpoint=handle_messages, methods=["POST"]),
        ],
        on_startup=[on_startup],
        on_shutdown=[on_shutdown],
    )


def run_server() -> None:
    """Run the MCP server (auto-detect mode from environment)."""
    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()

    if transport == "sse" or transport == "http":
        import uvicorn
        port = int(os.environ.get("PORT", "8000"))
        host = os.environ.get("HOST", "0.0.0.0")
        sse_app = create_sse_app()
        uvicorn.run(sse_app, host=host, port=port)
    else:
        asyncio.run(run_stdio_server())


if __name__ == "__main__":
    run_server()
