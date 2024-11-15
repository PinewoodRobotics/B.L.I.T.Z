import json

import numpy as np


def to_json(obj):
    def default(o):
        # Convert numpy arrays to lists
        if isinstance(o, np.ndarray):
            return o.tolist()
        # Use the object's __dict__ if it exists
        return getattr(
            o, "__dict__", str(o)
        )  # Fallback to `str(o)` if no `__dict__` exists

    return json.dumps(obj, default=default, sort_keys=True, indent=4)
