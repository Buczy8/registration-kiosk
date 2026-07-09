from __future__ import annotations

import asyncio
import random

from app.core.config import Settings


def get_simulated_printer_health(settings: Settings) -> bool:
    """Lokalny healthcheck drukarki (symulacja)."""
    return settings.print_enabled


async def simulate_printer_print(*, pdf_bytes: bytes, settings: Settings) -> None:
    """
    Symuluje wysłanie PDF do drukarki (bez fizycznej drukarki).

    pdf_bytes celowo nie jest logowane ani zapisywane - to tylko „ładunek” do
    symulacji czasu/niepowodzeń.
    """

    if settings.print_simulation_delay_seconds > 0:
        await asyncio.sleep(settings.print_simulation_delay_seconds)

    prob = settings.print_simulation_failure_probability
    if prob > 0 and random.random() < prob:
        raise RuntimeError("Simulated printer failure")

