"""Ready-to-run API backed by the small public demonstration bundle."""

from __future__ import annotations

import json
from pathlib import Path

from engine import CatalogBundle

from .main import create_app


DEMO_CATALOG = Path(__file__).resolve().parents[1] / "data" / "demo" / "catalog.json"


def load_demo_bundle() -> CatalogBundle:
    return CatalogBundle.from_mapping(json.loads(DEMO_CATALOG.read_text()))


app = create_app(load_demo_bundle())
