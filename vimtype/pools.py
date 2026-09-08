"""Pinned Monkeytype language resources, loaded only when selected."""

from functools import lru_cache
from importlib.resources import files
import json

POOLS = ("english", "english_1k", "english_5k", "english_10k", "english_25k", "english_450k")


@lru_cache(maxsize=len(POOLS))
def load_pool(name):
    if name not in POOLS:
        raise ValueError(f"Unknown word pool: {name}")
    resource = files("vimtype").joinpath("data", name + ".json")
    return tuple(json.loads(resource.read_text(encoding="utf-8"))["words"])
