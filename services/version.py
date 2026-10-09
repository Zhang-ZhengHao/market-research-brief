"""Build identity captured when the Streamlit process starts."""

from __future__ import annotations

import os


APP_VERSION = "0.1.0"


def normalize_build_sha(value: object) -> str:
    text = str(value or "").strip()
    return text[:12] if text else "dev"


BUILD_SHA = normalize_build_sha(os.getenv("INSIGHT_MONITOR_BUILD_SHA"))
