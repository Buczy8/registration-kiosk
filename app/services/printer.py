from __future__ import annotations

import asyncio
import random
import socket
import logging
from typing import Literal

from app.core.config import Settings

logger = logging.getLogger("app.printer")

PrinterConnectionStatus = Literal["ok", "error"]


async def _check_printer_tcp_connection(settings: Settings) -> bool:
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(settings.printer_host, settings.printer_port),
            timeout=1.0,
        )
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True
    except Exception as e:
        logger.warning(
            "Printer healthcheck failed for %s:%s: %s",
            settings.printer_host,
            settings.printer_port,
            e,
        )
        return False


async def get_printer_connection_status(settings: Settings) -> PrinterConnectionStatus:
    """
    Returns printer reachability for the admin dashboard (TCP to host:port).

    Independent of PRINT_ENABLED — that flag only controls whether users get
    auto-print after submitting a form; admin printing is always allowed.
    """
    if await _check_printer_tcp_connection(settings):
        return "ok"
    return "error"


async def get_printer_health(settings: Settings) -> bool:
    """True when the printer accepts a TCP connection on the configured port."""
    return (await get_printer_connection_status(settings)) == "ok"


async def send_print_job(*, pdf_bytes: bytes, settings: Settings, force: bool = False) -> None:
    """
    Sends the PDF bytes to the network printer using the RAW 9100 protocol.

    When force is False (user auto-print after submission), respects PRINT_ENABLED.
    Admin retries always pass force=True and are not gated by that flag.
    """
    if not settings.print_enabled and not force:
        raise RuntimeError("User printing is disabled in configuration")

    # Apply simulation delay if configured
    if settings.print_simulation_delay_seconds > 0:
        await asyncio.sleep(settings.print_simulation_delay_seconds)

    # Apply simulation failure probability if configured
    prob = settings.print_simulation_failure_probability
    if prob > 0 and random.random() < prob:
        raise RuntimeError("Simulated printer failure (random trigger)")

    logger.info(
        f"Connecting to network printer at {settings.printer_host}:{settings.printer_port} to send print job ({len(pdf_bytes)} bytes)"
    )

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(settings.printer_host, settings.printer_port),
            timeout=5.0
        )
    except asyncio.TimeoutError:
        raise ConnectionError(
            f"Connection timeout to printer at {settings.printer_host}:{settings.printer_port}"
        )
    except Exception as e:
        raise ConnectionError(
            f"Failed to connect to printer at {settings.printer_host}:{settings.printer_port}: {e}"
        )

    try:
        writer.write(pdf_bytes)
        await asyncio.wait_for(writer.drain(), timeout=5.0)
        logger.info("Print job sent successfully")
    except Exception as e:
        raise RuntimeError(f"Error during sending data to printer: {e}")
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
