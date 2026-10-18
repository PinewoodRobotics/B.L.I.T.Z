"""Create a runnable sample module and register it in deploy.py.

Stdlib-only so `scripts/backend.sh` can run this file directly with any
python3 before the project's virtual environment exists:

    python3 backend/deployment/module/scaffold.py --backend backend --name vision --language cpp
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re
import sys

# Stricter than BackendModules' folder rule: the name also becomes a CMake
# target, a Cargo package/binary, and a ProcessType member.
MODULE_NAME_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
CATALOG_IMPORT = "from backend.deployment.module.catalog import BackendModules"
MODULES_ASSIGNMENT = "modules = BackendModules(__file__)"


class ModuleLanguage(str, Enum):
    PYTHON = "python"
    RUST = "rust"
    CPP = "cpp"


@dataclass(frozen=True)
class ScaffoldResult:
    module_path: Path
    created_files: tuple[Path, ...]
    registered: bool
    manual_steps: str


def process_member_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "_", name).upper()


def sample_files(name: str, language: ModuleLanguage) -> dict[str, str]:
    """Relative path -> contents for a long-running hello-world program."""
    if language is ModuleLanguage.PYTHON:
        return {
            "__main__.py": f'''"""Sample BLITZ program for the {name} module."""
import os
import time


def main() -> None:
    system_name = os.environ.get("BLITZ_SYSTEM_NAME", "unknown")
    config_path = os.environ.get("BLITZ_CONFIG_PATH")
    print(f"{name} started on {{system_name}} (config: {{config_path}})")

    tick = 0
    while True:
        print(f"{name} heartbeat {{tick}}")
        tick += 1
        time.sleep(1.0)


if __name__ == "__main__":
    main()
''',
        }
    if language is ModuleLanguage.RUST:
        return {
            "Cargo.toml": f'''[package]
name = "{name}"
version = "0.1.0"
edition = "2021"

[dependencies]
''',
            "src/main.rs": f'''use std::{{env, thread, time::Duration}};

fn main() {{
    let system_name = env::var("BLITZ_SYSTEM_NAME").unwrap_or_else(|_| "unknown".into());
    let config_path = env::var("BLITZ_CONFIG_PATH").unwrap_or_default();
    println!("{name} started on {{system_name}} (config: {{config_path}})");

    let mut tick: u64 = 0;
    loop {{
        println!("{name} heartbeat {{tick}}");
        tick += 1;
        thread::sleep(Duration::from_secs(1));
    }}
}}
''',
        }
    return {
        "CMakeLists.txt": f'''cmake_minimum_required(VERSION 3.16)
project({name} LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
add_executable({name} main.cpp)
''',
        "main.cpp": f'''#include <chrono>
#include <cstdlib>
#include <iostream>
#include <thread>

int main() {{
    const char* system_name = std::getenv("BLITZ_SYSTEM_NAME");
    const char* config_path = std::getenv("BLITZ_CONFIG_PATH");
    std::cout << "{name} started on " << (system_name ? system_name : "unknown")
              << " (config: " << (config_path ? config_path : "") << ")" << std::endl;

    for (unsigned long tick = 0;; ++tick) {{
        std::cout << "{name} heartbeat " << tick << std::endl;
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }}
}}
''',
    }


def module_declaration(name: str, language: ModuleLanguage) -> str:
    return f'modules.{language.value}("{name}", process=ProcessType.{process_member_name(name)})'


def process_member(name: str) -> str:
    return f'{process_member_name(name)} = "{name}", 1.0'


def manual_registration(name: str, language: ModuleLanguage) -> str:
    member = process_member_name(name)
    return "\n".join((
        f"    {CATALOG_IMPORT}",
        f"    {MODULES_ASSIGNMENT}",
        "",
        "    class ProcessType(WeightedProcess):",
        f"        {process_member(name)}",
        "",
        "    # In get_modules():",
        f"        {module_declaration(name, language)},",
        "",
        "    # In pi_name_to_process_types():",
        f"        ProcessPlan[ProcessType]().add(ProcessType.{member}).assign(pi_names)",
    ))


class _SourceEditor:
    """Collects insertions/replacements by AST position and applies them bottom-up."""

    def __init__(self, source: str):
        self.source = source
        self._line_offsets = [0]
        for line in source.splitlines(keepends=True):
            self._line_offsets.append(self._line_offsets[-1] + len(line))
        self._edits: list[tuple[int, int, str]] = []

    def offset(self, lineno: int, col_offset: int) -> int:
        # AST columns are UTF-8 byte offsets.
        start = self._line_offsets[lineno - 1]
        line = self.source[start:self._line_offsets[lineno]]
        return start + len(line.encode("utf-8")[:col_offset].decode("utf-8", errors="ignore"))

    def line_indent(self, lineno: int) -> str:
        start = self._line_offsets[lineno - 1]
        line = self.source[start:]
        return line[: len(line) - len(line.lstrip(" \t"))]

    def replace(self, start: int, end: int, text: str) -> None:
        self._edits.append((start, end, text))

    def apply(self) -> str:
        result = self.source
        for start, end, text in sorted(self._edits, key=lambda edit: edit[0], reverse=True):
            result = result[:start] + text + result[end:]
        return result


def _top_level(tree: ast.Module, kind: type, name: str) -> ast.AST | None:
    return next((node for node in tree.body if isinstance(node, kind) and node.name == name), None)


def _defines_modules(tree: ast.Module) -> bool:
    return any(
        isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "modules" for target in node.targets)
        for node in tree.body
    )


def _imports_backend_modules(tree: ast.Module) -> bool:
    return any(
        isinstance(node, ast.ImportFrom) and any(alias.name == "BackendModules" for alias in node.names)
        for node in tree.body
    )


def _add_modules_helper(tree: ast.Module, editor: _SourceEditor) -> bool:
    imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    if not imports:
        return False
    last_import = imports[-1]
    position = editor.offset(last_import.end_lineno, last_import.end_col_offset)
    text = ""
    if not _imports_backend_modules(tree):
        text += f"\n{CATALOG_IMPORT}"
    text += f"\n\n{MODULES_ASSIGNMENT}"
    editor.replace(position, position, text)
    return True


def _add_process_member(class_node: ast.ClassDef, member: str, editor: _SourceEditor) -> bool:
    body = class_node.body
    if len(body) == 1 and isinstance(body[0], ast.Pass):
        statement = body[0]
        editor.replace(
            editor.offset(statement.lineno, statement.col_offset),
            editor.offset(statement.end_lineno, statement.end_col_offset),
            member,
        )
        return True
    last = body[-1]
    indent = editor.line_indent(body[0].lineno)
    position = editor.offset(last.end_lineno, last.end_col_offset)
    editor.replace(position, position, f"\n{indent}{member}")
    return True


def _add_module_declaration(function: ast.FunctionDef, declaration: str, editor: _SourceEditor) -> bool:
    returns = [node for node in ast.walk(function) if isinstance(node, ast.Return) and isinstance(node.value, ast.List)]
    if len(returns) != 1:
        return False
    statement = returns[0]
    module_list = statement.value
    if not module_list.elts:
        indent = editor.line_indent(statement.lineno)
        editor.replace(
            editor.offset(module_list.lineno, module_list.col_offset),
            editor.offset(module_list.end_lineno, module_list.end_col_offset),
            f"[\n{indent}    {declaration},\n{indent}]",
        )
        return True
    last = module_list.elts[-1]
    position = editor.offset(last.end_lineno, last.end_col_offset)
    separator = ""
    if editor.source[position:position + 1] == ",":
        position += 1
    else:
        separator = ","
    if last.end_lineno == module_list.end_lineno:
        editor.replace(position, position, f"{separator} {declaration}")
    else:
        editor.replace(position, position, f"{separator}\n{editor.line_indent(last.lineno)}{declaration},")
    return True


def _add_placement(function: ast.FunctionDef, member_name: str, editor: _SourceEditor) -> bool:
    assigns = [
        node for node in ast.walk(function)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "assign"
        and "ProcessPlan" in ast.unparse(node.func.value)
    ]
    if len(assigns) != 1:
        return False
    assign = assigns[0]
    chain = assign.func.value
    addition = f".add(ProcessType.{member_name})"
    returned = next((node for node in ast.walk(function) if isinstance(node, ast.Return) and node.value is assign), None)
    if returned is not None and assign.lineno == assign.end_lineno:
        # Expand `return ProcessPlan[...]().assign(...)` into the documented one-call-per-line style.
        segments: list[str] = []
        node: ast.expr = assign
        while isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            call_end = editor.offset(node.end_lineno, node.end_col_offset)
            segments.append(editor.source[editor.offset(node.func.value.end_lineno, node.func.value.end_col_offset):call_end].strip())
            node = node.func.value
        root = editor.source[editor.offset(node.lineno, node.col_offset):editor.offset(node.end_lineno, node.end_col_offset)]
        segments.reverse()
        segments.insert(len(segments) - 1, addition)
        indent = editor.line_indent(returned.lineno)
        lines = "".join(f"\n{indent}    {segment}" for segment in (root, *segments))
        editor.replace(
            editor.offset(assign.lineno, assign.col_offset),
            editor.offset(assign.end_lineno, assign.end_col_offset),
            f"({lines}\n{indent})",
        )
        return True
    position = editor.offset(chain.end_lineno, chain.end_col_offset)
    if assign.func.end_lineno != chain.end_lineno:
        addition = f"\n{editor.line_indent(assigns[0].func.end_lineno)}{addition}"
    editor.replace(position, position, addition)
    return True


def register_module(deploy_source: str, name: str, language: ModuleLanguage) -> str | None:
    """Return deploy.py source with the module registered, or None if its layout is unrecognized."""
    tree = ast.parse(deploy_source)
    process_class = _top_level(tree, ast.ClassDef, "ProcessType")
    modules_function = _top_level(tree, ast.FunctionDef, "get_modules")
    placement_function = _top_level(tree, ast.FunctionDef, "pi_name_to_process_types")
    if process_class is None or modules_function is None or placement_function is None:
        return None
    member_name = process_member_name(name)
    existing_members = {
        target.id for node in process_class.body if isinstance(node, ast.Assign)
        for target in node.targets if isinstance(target, ast.Name)
    }
    if member_name in existing_members:
        raise ValueError(f"ProcessType.{member_name} already exists in deploy.py")

    editor = _SourceEditor(deploy_source)
    registered = (
        (_defines_modules(tree) or _add_modules_helper(tree, editor))
        and _add_process_member(process_class, process_member(name), editor)
        and _add_module_declaration(modules_function, module_declaration(name, language), editor)
        and _add_placement(placement_function, member_name, editor)
    )
    if not registered:
        return None
    updated = editor.apply()
    try:
        ast.parse(updated)
    except SyntaxError:
        return None
    return updated


def scaffold_module(
    backend_path: Path, name: str, language: ModuleLanguage, deploy_file: str = "deploy.py",
) -> ScaffoldResult:
    if name == "common" or not MODULE_NAME_PATTERN.fullmatch(name):
        raise ValueError(
            f"Module name {name!r} must start with a letter and use only letters, digits, '_' or '-' "
            "(and cannot be 'common')."
        )
    module_path = backend_path / language.value / name
    if module_path.exists():
        raise FileExistsError(f"Module folder already exists: {module_path}")

    deploy_path = backend_path / deploy_file
    updated_deploy = None
    if deploy_path.is_file():
        updated_deploy = register_module(deploy_path.read_text(), name, language)

    created: list[Path] = []
    for relative, contents in sample_files(name, language).items():
        file_path = module_path / relative
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(contents)
        created.append(file_path)
    if updated_deploy is not None:
        deploy_path.write_text(updated_deploy)

    return ScaffoldResult(
        module_path=module_path,
        created_files=tuple(created),
        registered=updated_deploy is not None,
        manual_steps="" if updated_deploy is not None else manual_registration(name, language),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a sample BLITZ module.")
    parser.add_argument("--backend", required=True, type=Path, help="Backend folder containing deploy.py")
    parser.add_argument("--name", required=True, help="Module folder name")
    parser.add_argument("--language", required=True, choices=[language.value for language in ModuleLanguage])
    parser.add_argument("--deploy-file", default="deploy.py", help="Deployment file inside the backend folder")
    arguments = parser.parse_args(argv)

    try:
        result = scaffold_module(arguments.backend, arguments.name, ModuleLanguage(arguments.language), arguments.deploy_file)
    except (ValueError, FileExistsError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Created {arguments.language} module at {result.module_path}:")
    for file_path in result.created_files:
        print(f"  {file_path.relative_to(result.module_path)}")
    if result.registered:
        print(f"Registered ProcessType.{process_member_name(arguments.name)} in {arguments.deploy_file}; it runs once across the fleet.")
    else:
        print(f"Could not update {arguments.deploy_file} automatically. Add the following yourself:")
        print(result.manual_steps)
    return 0


if __name__ == "__main__":
    sys.exit(main())
