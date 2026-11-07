"""Runtime settings, read from the environment only.

This repository is public: project IDs, data store paths and service accounts are never hard-coded. Agent Engine
injects GOOGLE_CLOUD_PROJECT; deploy scripts pass the HIVE_* variables below.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    project: str
    region: str            # Cloud Run and BigQuery location
    engine_region: str     # Agent Engine location
    model_location: str    # Gemini endpoint location
    bq_dataset: str
    kb_prefix: str         # Vertex AI Search data store id prefix ("<prefix>-<realm>")
    kb_location: str

    def kb_data_store(self, realm: str) -> str:
        return (f"projects/{self.project}/locations/{self.kb_location}/collections/default_collection/"
                f"dataStores/{self.kb_prefix}-{realm}")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        project=os.environ.get("HIVE_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
        region=os.environ.get("HIVE_REGION", "us-central1"),
        engine_region=os.environ.get("HIVE_ENGINE_REGION", "us-east4"),
        model_location=os.environ.get("HIVE_MODEL_LOCATION", "global"),
        bq_dataset=os.environ.get("HIVE_BQ_DATASET", "agenthive_demo"),
        kb_prefix=os.environ.get("HIVE_KB_PREFIX", "agenthive-kb"),
        kb_location=os.environ.get("HIVE_KB_LOCATION", "global"),
    )
