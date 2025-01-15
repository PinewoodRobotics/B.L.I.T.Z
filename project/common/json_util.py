import json

import numpy as np


def to_json(obj):
    def default(o):
        if isinstance(o, np.ndarray):
            return o.tolist()
        return getattr(o, "__dict__", str(o))

    return json.dumps(obj, default=default, sort_keys=True, indent=4)
