import os
import json
from typing import Iterator, Dict, Any

def iter_jsonl_folder(base_folder: str, entity_name: str) -> Iterator[Dict[str, Any]]:
    """Yields parsed JSON objects from all .jsonl files in a specific entity folder."""
    folder_path = os.path.join(base_folder, entity_name)
    if not os.path.exists(folder_path):
        return
    for filename in os.listdir(folder_path):
        if filename.endswith(".jsonl"):
            with open(os.path.join(folder_path, filename), "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            continue
