"""Shared application context passed to every page.

Pages never import concrete services or reach into the main window directly;
they talk to this small context object, which keeps them decoupled and testable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from services.registry import Services


@dataclass
class AppContext:
    services: Services
    navigate: Callable[..., None]        # navigate(key, **params)
    toast: Callable[..., None]           # toast(message, tone="info")
    set_theme: Callable[[str], None]     # set_theme("light" | "dark")
    current_theme: Callable[[], str]
