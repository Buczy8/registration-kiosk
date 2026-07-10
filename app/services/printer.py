from __future__ import annotations

import asyncio
import random
import socket
import logging

from app.core.config import Settings

logger = logging.getLogger("app.printer")


def get_printer_health(settings: Settings) -> bool:
    """
    Checks the status of the network printer.
    If printing is disabled, returns False.
    Otherwise, attempts a quick TCP connection to the printer host/port to check status.
    """
    if not settings.print_enabled:
        return False

    try:
        # Quick synchronous connection check
        with socket.create_connection(
            (settings.printer_host, settings.printer_port),
            timeout=1.0
        ):
            return True
    except Exception as e:
        logger.warning(
            f"Printer healthcheck failed for {settings.printer_host}:{settings.printer_port}: {e}"
        )
        return False


async def send_print_job(*, pdf_bytes: bytes, settings: Settings, force: bool = False) -> None:
    """
    Sends the PDF bytes to the network printer using the RAW 9100 protocol.
    If printing is disabled and force is False, raises a RuntimeError.
    Applies simulation delay and failure probability if configured in settings.
    """
    if not settings.print_enabled and not force:
        raise RuntimeError("Printing is disabled in configuration")

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
