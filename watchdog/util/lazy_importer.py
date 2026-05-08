from __future__ import annotations

# pyright: reportAny=false, reportExplicitAny=false, reportImplicitOverride=false, reportUninitializedInstanceVariable=false

from collections.abc import Callable
import functools
import importlib
import sys
from typing import Any, TypeVar, cast


TClass = TypeVar("TClass", bound=type[Any])
TFunction = TypeVar("TFunction", bound=Callable[..., Any])


class LazyImportError(RuntimeError):
    pass


def _import_or_reload_module(module_path: str) -> Any:
    importlib.invalidate_caches()
    if module_path in sys.modules:
        return importlib.reload(sys.modules[module_path])
    return importlib.import_module(module_path)


def _has_matching_class_identity(value: Any, target: type[Any]) -> bool:
    target_module = target.__module__
    target_name = target.__qualname__
    return any(
        candidate.__module__ == target_module and candidate.__qualname__ == target_name
        for candidate in type(value).__mro__
    )


def _has_matching_subclass_identity(subclass: type[Any], target: type[Any]) -> bool:
    target_module = target.__module__
    target_name = target.__qualname__
    return any(
        candidate.__module__ == target_module and candidate.__qualname__ == target_name
        for candidate in subclass.__mro__
    )


class _LazyImportedClassMeta(type):
    _lazy_import_module_path: str
    _lazy_import_symbol_name: str
    _lazy_import_target_cache: type[Any] | None

    def _lazy_import_target(cls) -> type[Any]:
        module = _import_or_reload_module(cls._lazy_import_module_path)
        target = getattr(module, cls._lazy_import_symbol_name, None)
        if not isinstance(target, type):
            raise LazyImportError(
                f"{cls._lazy_import_module_path}.{cls._lazy_import_symbol_name} "
                + "is not an importable class"
            )

        cls._lazy_import_target_cache = target
        return target

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        return cls._lazy_import_target()(*args, **kwargs)

    def __getattr__(cls, name: str) -> Any:
        return getattr(cls._lazy_import_target(), name)

    def __instancecheck__(cls, instance: Any) -> bool:
        target = cls._lazy_import_target()
        return isinstance(instance, target) or _has_matching_class_identity(
            instance, target
        )

    def __subclasscheck__(cls, subclass: type[Any]) -> bool:
        target = cls._lazy_import_target()
        return issubclass(subclass, target) or _has_matching_subclass_identity(
            subclass, target
        )


def lazy_import_class(
    module_path: str,
    *,
    class_name: str | None = None,
) -> Callable[[TClass], TClass]:
    def decorator(stub_class: TClass) -> TClass:
        namespace = {
            key: value
            for key, value in stub_class.__dict__.items()
            if key not in {"__dict__", "__weakref__"}
        }
        namespace["_lazy_import_module_path"] = module_path
        namespace["_lazy_import_symbol_name"] = class_name or stub_class.__name__
        namespace["_lazy_import_target_cache"] = None

        lazy_class = _LazyImportedClassMeta(
            stub_class.__name__,
            stub_class.__bases__,
            namespace,
        )
        return cast(TClass, cast(object, lazy_class))

    return decorator


def lazy_import_function(
    module_path: str,
    *,
    function_name: str | None = None,
) -> Callable[[TFunction], TFunction]:
    def decorator(stub_function: TFunction) -> TFunction:
        symbol_name = function_name or stub_function.__name__

        @functools.wraps(stub_function)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            module = _import_or_reload_module(module_path)
            imported = getattr(module, symbol_name, None)
            if not callable(imported):
                raise LazyImportError(
                    f"{module_path}.{symbol_name} is not an importable function"
                )
            return imported(*args, **kwargs)

        return cast(TFunction, wrapper)

    return decorator
