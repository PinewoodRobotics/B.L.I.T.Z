from __future__ import annotations

# pyright: reportAny=false, reportExplicitAny=false, reportUnusedParameter=false

import importlib
import sys
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from watchdog.util.lazy_importer import (
    LazyImportError,
    lazy_import_class,
    lazy_import_function,
)


def write_module(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    module_name: str,
    source: str,
) -> str:
    module_path = tmp_path / f"{module_name}.py"
    _ = module_path.write_text(source)
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop(module_name, None)
    importlib.invalidate_caches()
    return module_name


def test_lazy_import_class_imports_only_when_used(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
):
    module_name = write_module(
        tmp_path,
        monkeypatch,
        "lazy_class_fixture",
        """
class RemoteThing:
    class_value = "loaded"

    def __init__(self, value: str):
        self.value = value

    def describe(self) -> str:
        return f"remote:{self.value}"
""",
    )

    @lazy_import_class(module_name, class_name="RemoteThing")
    class LocalThing:
        class_value: str

        def describe(self) -> str: ...

    assert module_name not in sys.modules

    instance = LocalThing("value")

    assert module_name in sys.modules
    assert isinstance(instance, LocalThing)
    assert LocalThing.class_value == "loaded"
    assert instance.describe() == "remote:value"


def test_lazy_import_class_reloads_before_each_resolution(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
):
    value_file = tmp_path / "class_value.txt"
    _ = value_file.write_text("first")
    module_name = write_module(
        tmp_path,
        monkeypatch,
        "lazy_reload_class_fixture",
        f"""
from pathlib import Path

class RemoteThing:
    class_value = Path({str(value_file)!r}).read_text().strip()

    def describe(self) -> str:
        return self.class_value
""",
    )

    @lazy_import_class(module_name, class_name="RemoteThing")
    class LocalThing:
        class_value: str

        def describe(self) -> str: ...

    assert LocalThing.class_value == "first"

    _ = value_file.write_text("second")

    assert LocalThing.class_value == "second"
    assert LocalThing().describe() == "second"


def test_lazy_import_class_supports_subclass_checks(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
):
    module_name = write_module(
        tmp_path,
        monkeypatch,
        "lazy_subclass_fixture",
        """
class RemoteBase:
    pass

class RemoteChild(RemoteBase):
    pass
""",
    )

    imported_module = importlib.import_module(module_name)
    remote_child = imported_module.RemoteChild

    @lazy_import_class(module_name, class_name="RemoteBase")
    class LocalBase:
        pass

    assert issubclass(remote_child, LocalBase)


def test_lazy_import_function_imports_only_when_called(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
):
    module_name = write_module(
        tmp_path,
        monkeypatch,
        "lazy_function_fixture",
        """
def remote_add(left: int, right: int) -> int:
    return left + right
""",
    )

    @lazy_import_function(module_name, function_name="remote_add")
    def add(left: int, right: int) -> int: ...

    assert module_name not in sys.modules

    assert add(2, 3) == 5
    assert module_name in sys.modules


def test_lazy_import_function_reloads_before_each_call(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
):
    value_file = tmp_path / "function_value.txt"
    _ = value_file.write_text("first")
    module_name = write_module(
        tmp_path,
        monkeypatch,
        "lazy_reload_function_fixture",
        f"""
from pathlib import Path

VALUE = Path({str(value_file)!r}).read_text().strip()

def remote_value() -> str:
    return VALUE
""",
    )

    @lazy_import_function(module_name, function_name="remote_value")
    def value() -> str: ...

    assert value() == "first"

    _ = value_file.write_text("second")

    assert value() == "second"


def test_lazy_import_errors_for_missing_or_wrong_symbol(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
):
    module_name = write_module(
        tmp_path,
        monkeypatch,
        "lazy_error_fixture",
        "not_callable = 123\n",
    )

    @lazy_import_class(module_name, class_name="not_callable")
    class MissingClass:
        pass

    @lazy_import_function(module_name, function_name="not_callable")
    def missing_function() -> int: ...

    with pytest.raises(LazyImportError):
        _ = MissingClass()

    with pytest.raises(LazyImportError):
        _ = missing_function()
