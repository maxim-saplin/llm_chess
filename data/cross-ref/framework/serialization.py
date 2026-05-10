from __future__ import annotations

import math


def json_safe(value):
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    try:
        if math.isnan(value):
            return None
    except TypeError:
        pass
    return value