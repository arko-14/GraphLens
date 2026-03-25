import os
from typing import Dict, Any

def clean_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Basic cleaning: remove empty strings, fix nested objects to strings."""
    cleaned = {}
    for k, v in d.items():
        if v == "" or v is None:
            continue
        if isinstance(v, dict):
            # some time fields are dicts {"hours":...} - ignore them or convert
            continue
        cleaned[k] = v
    return cleaned
