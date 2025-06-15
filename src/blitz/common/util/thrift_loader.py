from thrift.Thrift import TType
from enum import IntEnum
import inspect
from typing import get_type_hints


def _convert_value(ttype, spec, raw):
    """Recursively convert raw JSON/dict/list into thrift objects/primitives."""
    if raw is None:
        return None

    # STRUCT → spec is (Class, thrift_spec)
    if ttype == TType.STRUCT:
        cls, _ = spec
        return dict_to_thrift(cls, raw)

    # LIST → spec is (elem_ttype, elem_spec, ...)
    if ttype == TType.LIST:
        # only take the first two elements (etype, espec)
        etype, espec = spec[0], spec[1]
        return [_convert_value(etype, espec, elt) for elt in raw]

    # SET → spec is same as LIST
    if ttype == TType.SET:
        etype, espec = spec[0], spec[1]
        return set(_convert_value(etype, espec, elt) for elt in raw)

    # MAP → spec is (key_ttype, key_spec, val_ttype, val_spec, ...)
    if ttype == TType.MAP:
        ktype, kspec, vtype, vspec = spec[0], spec[1], spec[2], spec[3]
        return {
            _convert_value(ktype, kspec, k): _convert_value(vtype, vspec, v)
            for k, v in raw.items()
        }

    # Primitives (BOOL, BYTE, I16, I32, I64, DOUBLE, STRING, BINARY, ENUM)
    return raw


def dict_to_thrift(cls, data: dict):
    """
    Instantiate a Thrift-generated class `cls` from a plain dict `data`,
    recursing into nested structs, lists, maps, and sets.
    """
    kwargs = {}
    for field in getattr(cls, "thrift_spec", ())[1:]:
        if not field:
            continue
        # field: (field_id, ttype, name, type_spec, default)
        _, ttype, fname, ftype_spec, _ = field
        if fname in data:
            raw_val = data[fname]
            converted = _convert_value(ttype, ftype_spec, raw_val)
            # Handle enum fields based on __init__ type hints
            enum_type = None
            init_fn = getattr(cls, "__init__", None)
            if init_fn:
                try:
                    hints = get_type_hints(init_fn)
                    enum_type = hints.get(fname)
                except Exception:
                    enum_type = None
            if (
                enum_type
                and isinstance(converted, (int, str))
                and isinstance(enum_type, type)
                and issubclass(enum_type, IntEnum)
            ):
                converted = enum_type(converted)
            kwargs[fname] = converted
    return cls(**kwargs)
