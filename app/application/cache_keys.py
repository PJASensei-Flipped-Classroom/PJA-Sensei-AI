import hashlib
import json
from typing import Dict, List


def build_cache_key(system_prompt: str, messages: List[Dict[str, str]], model: str = "default") -> str:
    canonical_payload = json.dumps(
        {
            "model": model,
            "system_prompt": system_prompt,
            "messages": messages,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
