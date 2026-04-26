import os
import re
import shutil
import sys
import textwrap
import time
from collections.abc import Callable, Sequence
from collections import deque


INDENT = "  "
OUTPUT_INDENT = f"{INDENT}  "
ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
STATUS_WIDTH = 112
_context: str | None = None
BOX_WIDTH = 104
CONSOLE_TAIL_LINES = 5
CLEAR_SCREEN_AND_SCROLLBACK = "\033[2J\033[3J\033[H"
_active_display: "LiveBundleDisplay | None" = None
_active_deployment_display: "LiveDeploymentDisplay | None" = None
_current_module_index: int | None = None
_mode: str = os.environ.get(
    "BLITZ_LOGGER_MODE",
    os.environ.get("BLITZ_BUNDLE_OUTPUT", "live"),
).lower()
_logger_failed: bool = False
_advanced_enabled: bool = os.environ.get("BLITZ_ADVANCED") == "1"


def _should_color() -> bool:
    return "NO_COLOR" not in os.environ and sys.stdout.isatty()


def _color(value: str, color_code: str) -> str:
    if not _should_color():
        return value

    return f"\033[{color_code}m{value}\033[0m"


def _cyan(value: str) -> str:
    return _color(value, "36")


def _green(value: str) -> str:
    return _color(value, "32")


def _red(value: str) -> str:
    return _color(value, "31")


def _yellow(value: str) -> str:
    return _color(value, "33")


def _magenta(value: str) -> str:
    return _color(value, "35")


def _dim(value: str) -> str:
    return _color(value, "2")


def _bold(value: str) -> str:
    return _color(value, "1")


def set_mode(mode: str) -> None:
    global _mode
    _mode = mode.lower()


def enable_output() -> None:
    set_mode("live")


def disable_output() -> None:
    set_mode("silent")


def set_output_enabled(enabled: bool) -> None:
    if enabled:
        enable_output()
    else:
        disable_output()


def enable_live_output() -> None:
    set_mode("live")


def enable_plain_output() -> None:
    set_mode("plain")


def enable_silent_output() -> None:
    set_mode("silent")


def enable_advanced_output() -> None:
    global _advanced_enabled
    _advanced_enabled = True


def disable_advanced_output() -> None:
    global _advanced_enabled
    _advanced_enabled = False


def set_advanced_output(enabled: bool) -> None:
    if enabled:
        enable_advanced_output()
    else:
        disable_advanced_output()


def set_verbosity(enabled: bool) -> None:
    if enabled:
        os.environ["BLITZ_VERBOSE"] = "1"
    else:
        _ = os.environ.pop("BLITZ_VERBOSE", None)


def set_verbose(enabled: bool) -> None:
    set_verbosity(enabled)


def enable_verbose_output() -> None:
    set_verbosity(True)


def disable_verbose_output() -> None:
    set_verbosity(False)


def enable_color() -> None:
    _ = os.environ.pop("NO_COLOR", None)


def disable_color() -> None:
    os.environ["NO_COLOR"] = "1"


def set_color_enabled(enabled: bool) -> None:
    if enabled:
        enable_color()
    else:
        disable_color()


def reset_logger_failure() -> None:
    global _logger_failed
    _logger_failed = False


def get_mode() -> str:
    if _advanced_enabled:
        return "advanced"
    return _mode


def silent_enabled() -> bool:
    return get_mode() in {"silent", "off", "none"}


def live_enabled() -> bool:
    return get_mode() == "live" and not _verbose_enabled()


def advanced_enabled() -> bool:
    return get_mode() == "advanced"


def plain_enabled() -> bool:
    return get_mode() == "plain"


def _fit_box_line(value: str) -> str:
    box_inner_width = _box_inner_width()
    visible_length = len(strip_ansi(value))
    if visible_length > box_inner_width:
        value = strip_ansi(value)[: box_inner_width - 3] + "..."
        visible_length = len(value)

    return value + (" " * (box_inner_width - visible_length))


def _box_width() -> int:
    terminal_width = shutil.get_terminal_size(fallback=(BOX_WIDTH, 24)).columns
    return max(40, min(BOX_WIDTH, terminal_width - 2))


def _box_inner_width() -> int:
    return _box_width() - 4


def _box_border(border_state: str | None = None) -> str:
    return _color_box_border("+" + "-" * (_box_width() - 2) + "+", border_state)


def _reset_screen() -> None:
    print(CLEAR_SCREEN_AND_SCROLLBACK, end="")


def _box_line(value: str = "", border_state: str | None = None) -> str:
    border = _color_box_border("|", border_state)
    return f"{border} {_fit_box_line(value)} {border}"


def _color_box_border(line: str, state: str | None = None) -> str:
    if state == "failed":
        return _red(line)
    if state == "running":
        return _yellow(line)
    return _green(line)


def _box_wrapped_lines(
    value: str,
    subsequent_indent: int = 0,
    border_state: str | None = None,
) -> list[str]:
    width = max(20, _box_inner_width() - subsequent_indent)
    wrapped = textwrap.wrap(strip_ansi(value), width=width) or [""]
    lines: list[str] = []
    for index, line in enumerate(wrapped):
        prefix = " " * subsequent_indent if index > 0 else ""
        lines.append(_box_line(prefix + line, border_state))

    return lines


def set_context(context: str) -> None:
    global _context
    _context = context


def clear_context() -> None:
    global _context
    _context = None


class LiveBundleDisplay:
    def __init__(
        self,
        bundle_name: str,
        system: str,
        module_labels: Sequence[str],
    ):
        self.bundle_name: str = bundle_name
        self.system: str = system
        self.module_states: list[str] = ["waiting" for _ in module_labels]
        self.module_steps: list[str] = ["" for _ in module_labels]
        self.module_console: list[deque[str]] = [
            deque(maxlen=CONSOLE_TAIL_LINES) for _ in module_labels
        ]
        self.module_labels: list[str] = list(module_labels)
        self.archive_state: str = "waiting"
        self.archive_step: str = ""
        self.start_time: float = time.monotonic()
        self._rendered_lines: int = 0
        self._finished: bool = False

    def start(self) -> None:
        self.render()

    def set_module_step(self, module_index: int, step_message: str) -> None:
        self.module_states[module_index] = "running"
        self.module_steps[module_index] = step_message
        self.render()

    def add_module_console_line(self, module_index: int, line: str) -> None:
        clean_line = _format_status_line(line)
        if not clean_line:
            return

        self.module_console[module_index].append(clean_line)
        self.render()

    def complete_module(self, module_index: int, step_message: str = "ready") -> None:
        self.module_states[module_index] = "done"
        self.module_steps[module_index] = step_message
        self.module_console[module_index].clear()
        self.render()

    def fail_module(self, module_index: int, step_message: str) -> None:
        self.module_states[module_index] = "failed"
        self.module_steps[module_index] = step_message
        self.render()

    def set_archive_step(self, step_message: str) -> None:
        self.archive_state = "running"
        self.archive_step = step_message
        self.render()

    def finish(self, archive_path: str) -> None:
        self.archive_state = "done"
        self.archive_step = archive_path
        self._finished = True
        self.render(force_print=True)
        clear_live_display()

    def render(self, force_print: bool = False) -> None:
        if not _live_status_enabled() and not force_print:
            return

        lines = self._build_lines()
        if _live_status_enabled():
            _reset_screen()
        print("\n".join(lines), flush=True)
        self._rendered_lines = len(lines)

    def _build_lines(self) -> list[str]:
        elapsed = time.monotonic() - self.start_time
        done_count = sum(1 for state in self.module_states if state == "done")
        panel_state = _panel_state(
            self.module_states,
            self.archive_state,
        )
        title = f"BUNDLE {self.bundle_name}"
        summary = (
            f"system {self.system} | modules {done_count}/{len(self.module_labels)} "
            f"| elapsed {elapsed:0.1f}s"
        )
        lines = [
            _box_border(panel_state),
            _box_line(_bold(_green(title)), panel_state),
            _box_line(_dim(summary), panel_state),
            _box_border(panel_state),
        ]

        for index, label in enumerate(self.module_labels):
            state = self.module_states[index]
            step_message = self.module_steps[index] or "waiting"
            lines.extend(_status_row_lines(state, label, step_message, panel_state))
            if state == "running" and self.module_console[index]:
                lines.append(_box_line(_magenta("      console"), panel_state))
                for console_line in self.module_console[index]:
                    lines.extend(
                        _box_wrapped_lines(
                            _dim(f"        {console_line}"),
                            8,
                            panel_state,
                        )
                    )

        archive_step = self.archive_step or "waiting"
        lines.extend(
            _status_row_lines(
                self.archive_state,
                "archive",
                archive_step,
                panel_state,
            )
        )
        lines.append(_box_border(panel_state))
        return lines


class LiveDeploymentDisplay:
    def __init__(self, title: str):
        self.title: str = title
        self.phase: str = "starting"
        self.phase_state: str = "running"
        self.phase_step: str = ""
        self.stage_rows: dict[str, tuple[str, str]] = {}
        self.system_rows: dict[str, tuple[str, str]] = {}
        self.events: deque[str] = deque(maxlen=6)
        self.start_time: float = time.monotonic()
        self.spinner_index: int = 0
        self._rendered_lines: int = 0

    def set_phase(self, phase: str, step: str = "", state: str = "running") -> None:
        self.phase = phase
        self.phase_step = step
        self.phase_state = state
        self.render()

    def tick(self, step: str | None = None) -> None:
        self.spinner_index += 1
        if step is not None:
            self.phase_step = step
        self.render()

    def set_system(self, label: str, state: str, step: str) -> None:
        self.system_rows[label] = (state, step)
        self.render()

    def set_stage(self, label: str, state: str, step: str) -> None:
        self.stage_rows[label] = (state, step)
        self.phase = label
        self.phase_state = state
        self.phase_step = step
        self.render()

    def add_event(self, message: str) -> None:
        self.events.append(_format_status_line(message))
        self.render()

    def finish(self, step: str = "done") -> None:
        self.phase_state = "done"
        self.phase_step = step
        self.render(force_print=True)
        clear_deployment_display()

    def render(self, force_print: bool = False) -> None:
        if not _live_status_enabled() and not force_print:
            return

        lines = self._build_lines()
        if _live_status_enabled():
            _reset_screen()
        print("\n".join(lines), flush=True)
        self._rendered_lines = len(lines)

    def _build_lines(self) -> list[str]:
        elapsed = time.monotonic() - self.start_time
        panel_state = self._panel_state()
        spinner = self._spinner() if self.phase_state == "running" else " "
        summary = (
            f"{spinner} {self.phase}: {self.phase_step or self.phase_state} "
            f"| elapsed {elapsed:0.1f}s"
        )

        lines = [
            _box_border(panel_state),
            _box_line(_bold(_green(self.title)), panel_state),
            _box_line(_dim(summary), panel_state),
            _box_border(panel_state),
        ]

        if self.stage_rows:
            lines.append(_box_line(_magenta("stages"), panel_state))
            for label, (state, step) in self.stage_rows.items():
                lines.extend(_status_row_lines(state, label, step, panel_state))

        if self.system_rows:
            lines.append(_box_line(_magenta("systems"), panel_state))
            for label, (state, step) in sorted(self.system_rows.items()):
                lines.extend(_status_row_lines(state, label, step, panel_state))
        else:
            lines.append(_box_line(_dim("WAIT systems: none yet"), panel_state))

        if self.events and _live_events_enabled():
            lines.append(_box_line(_magenta("recent"), panel_state))
            for event in self.events:
                lines.extend(_box_wrapped_lines(_dim(f"  {event}"), 2, panel_state))

        lines.append(_box_border(panel_state))
        return lines

    def _panel_state(self) -> str | None:
        if self.phase_state == "failed":
            return "failed"
        if any(state == "failed" for state, _ in self.stage_rows.values()):
            return "failed"
        if any(state == "failed" for state, _ in self.system_rows.values()):
            return "failed"
        if self.phase_state == "running":
            return "running"
        if any(state == "running" for state, _ in self.stage_rows.values()):
            return "running"
        if any(state == "running" for state, _ in self.system_rows.values()):
            return "running"
        return None

    def _spinner(self) -> str:
        return (".", "o", "O", "o")[self.spinner_index % 4]


def _panel_state(module_states: list[str], archive_state: str) -> str | None:
    if "failed" in module_states or archive_state == "failed":
        return "failed"
    if "running" in module_states or archive_state == "running":
        return "running"
    return None


def _state_marker(state: str) -> str:
    if state == "done":
        return "DONE"
    if state == "running":
        return "RUN "
    if state == "failed":
        return "FAIL"
    return "WAIT"


def _colored_state_marker(state: str) -> str:
    marker = _state_marker(state)
    if state == "done":
        return _green(marker)
    if state == "running":
        return _yellow(marker)
    if state == "failed":
        return _red(marker)
    return _dim(marker)


def _colored_step(state: str, step_message: str) -> str:
    if state == "done":
        return _green(step_message)
    if state == "running":
        return _yellow(step_message)
    if state == "failed":
        return _red(step_message)
    return _dim(step_message)


def _colored_label(label: str, state: str) -> str:
    if label == "archive":
        return _bold(_magenta(label)) if state == "running" else _magenta(label)

    match = re.match(r"^(?P<name>.+?) (?P<language>\([^)]+\))$", label)
    if match is None:
        return _bold(label) if state == "running" else label

    name = match.group("name")
    language = match.group("language")
    name_text = _bold(name) if state == "running" else name
    return f"{name_text} {_magenta(language)}"


def _status_row_lines(
    state: str,
    label: str,
    step_message: str,
    border_state: str | None,
) -> list[str]:
    marker = _state_marker(state)
    plain_prefix = f"{marker} {label}: "
    first_width = max(20, _box_inner_width() - len(plain_prefix))
    continuation_indent = 6
    continuation_width = max(20, _box_inner_width() - continuation_indent)
    wrapped_steps = textwrap.wrap(step_message, width=first_width) or [""]

    lines = [
        _box_line(
            (
                f"{_colored_state_marker(state)} {_colored_label(label, state)}: "
                f"{_colored_step(state, wrapped_steps[0])}"
            ),
            border_state,
        )
    ]

    for step_line in textwrap.wrap(
        " ".join(wrapped_steps[1:]),
        width=continuation_width,
    ):
        lines.append(
            _box_line(
                (" " * continuation_indent) + _colored_step(state, step_line),
                border_state,
            )
        )

    return lines


def set_live_display(display: LiveBundleDisplay) -> None:
    global _active_display
    _active_display = display


def clear_live_display() -> None:
    global _active_display, _current_module_index
    _active_display = None
    _current_module_index = None


def set_deployment_display(display: LiveDeploymentDisplay) -> None:
    global _active_deployment_display
    _active_deployment_display = display


def clear_deployment_display() -> None:
    global _active_deployment_display
    _active_deployment_display = None


def set_current_module(module_index: int | None) -> None:
    global _current_module_index
    _current_module_index = module_index


def complete_current_module(step_message: str = "ready") -> None:
    if _active_display is None or _current_module_index is None:
        return

    _active_display.complete_module(_current_module_index, step_message)


def complete_active_module_if_running(step_message: str = "assembled") -> None:
    if _active_display is None or _current_module_index is None:
        return

    if _active_display.module_states[_current_module_index] == "running":
        _active_display.complete_module(_current_module_index, step_message)


def add_current_console_line(line: str) -> None:
    if _active_display is None or _current_module_index is None:
        return

    _active_display.add_module_console_line(_current_module_index, line)


def set_archive_step(step_message: str) -> None:
    if _active_display is None:
        return

    _active_display.set_archive_step(step_message)


def finish_live_display(archive_path: str) -> None:
    if _active_display is None:
        return

    _active_display.finish(archive_path)


def refresh_deployment_display() -> None:
    if _active_deployment_display is None or not live_enabled():
        return

    _active_deployment_display.render(force_print=True)


def start_bundle(
    bundle_name: str,
    system_key: str,
    module_labels: Sequence[str],
    build_path: str,
) -> None:
    if silent_enabled():
        return

    if advanced_enabled():
        set_context(bundle_name)
        bundle_header(bundle_name)
        detail("modules", len(module_labels))
        detail("system", system_key)
        detail("build path", build_path)
        return

    if plain_enabled() or _verbose_enabled():
        print(f"Bundling {len(module_labels)} modules into {bundle_name}")
        print(f"System: {system_key}")
        print(f"Build path: {build_path}")
        print()
        return

    if live_enabled():
        display = LiveBundleDisplay(bundle_name, system_key, module_labels)
        set_live_display(display)
        display.start()


def start_module(
    module_index: int,
    total_modules: int,
    module_name: str,
    language_name: str,
) -> None:
    if silent_enabled():
        return

    complete_active_module_if_running()
    set_current_module(module_index - 1)
    if plain_enabled() or _verbose_enabled():
        print(f"[{module_index}/{total_modules}] {module_name} ({language_name})")
        return

    section(f"Module {module_index}/{total_modules}: {module_name} ({language_name})")


def complete_module(message: str = "assembled") -> None:
    if silent_enabled():
        return

    if live_enabled():
        complete_current_module(message)
    elif plain_enabled() or _verbose_enabled():
        print()


def start_archive(archive_base_path: str) -> None:
    if silent_enabled():
        return

    complete_active_module_if_running()
    set_current_module(None)
    if live_enabled():
        set_archive_step("creating archive")
        return

    if plain_enabled() or _verbose_enabled():
        print(f"Creating archive {archive_base_path}")
        return

    section("Archive")
    detail("base path", archive_base_path)


def finish_bundle(archive_path: str) -> None:
    if silent_enabled():
        return

    if live_enabled():
        finish_live_display(os.path.relpath(archive_path))
        refresh_deployment_display()
        return

    if plain_enabled() or _verbose_enabled():
        print(f"Archive path: {archive_path}")
        return

    success(f"Created {archive_path}")
    bundle_footer()
    clear_context()


def start_deployment(title: str = "DEPLOYMENT") -> None:
    if silent_enabled():
        return

    if plain_enabled() or advanced_enabled() or _verbose_enabled():
        section(title)
        return

    if live_enabled():
        display = LiveDeploymentDisplay(title)
        set_deployment_display(display)
        display.set_phase("deploy", "starting")


def start_discovery(timeout_seconds: float) -> None:
    if silent_enabled():
        return

    if _active_deployment_display is not None and live_enabled():
        _active_deployment_display.set_stage(
            "discovery",
            "running",
            f"searching network for {timeout_seconds:0.1f}s",
        )
        return

    step(f"Discover systems on network for {timeout_seconds:0.1f}s")


def discovery_tick(remaining_seconds: float) -> None:
    if silent_enabled():
        return

    if _active_deployment_display is not None and live_enabled():
        _active_deployment_display.tick(f"{remaining_seconds:0.1f}s remaining")


def discovered_system(system_name: str, hostname: str, system_key: str) -> None:
    label = f"{system_name} ({hostname})"
    if silent_enabled():
        return

    if _active_deployment_display is not None and live_enabled():
        _active_deployment_display.set_system(label, "done", system_key)
        _active_deployment_display.add_event(f"discovered {label}")
        return

    success(f"Discovered {label}")
    detail("system", system_key)


def finish_discovery(system_count: int) -> None:
    if silent_enabled():
        return

    message = f"found {system_count} system{'s' if system_count != 1 else ''}"
    if _active_deployment_display is not None and live_enabled():
        _active_deployment_display.set_stage("discovery", "done", message)
        return

    success(message)


def deployment_stage(label: str, state: str, message: str) -> None:
    if silent_enabled():
        return

    if _active_deployment_display is not None and live_enabled():
        _active_deployment_display.set_stage(label, state, message)
        return

    if state == "done":
        success(f"{label}: {message}")
    elif state == "failed":
        failure(f"{label}: {message}")
    else:
        step(f"{label}: {message}")


def deployment_event(message: str) -> None:
    if silent_enabled():
        return

    if _active_deployment_display is not None and live_enabled():
        _active_deployment_display.add_event(message)
        return

    detail("event", message)


def start_rsync(system_labels: Sequence[str]) -> None:
    if silent_enabled():
        return

    if _active_deployment_display is not None and live_enabled():
        display = _active_deployment_display
        for label in system_labels:
            display.system_rows[label] = ("waiting", "waiting")
        display.set_stage("rsync", "running", "deploying bundles")
        return

    if live_enabled():
        display = LiveDeploymentDisplay("DEPLOYMENT")
        set_deployment_display(display)
        for label in system_labels:
            display.system_rows[label] = ("waiting", "waiting")
        display.set_stage("rsync", "running", "deploying bundles")
        return

    section("Rsync")
    detail("systems", len(system_labels))


def rsync_step(system_label: str, message: str) -> None:
    if silent_enabled():
        return

    if _active_deployment_display is not None and live_enabled():
        _active_deployment_display.set_system(system_label, "running", message)
        _active_deployment_display.add_event(f"{system_label}: {message}")
        return

    step(f"{system_label}: {message}")


def rsync_success(system_label: str, message: str) -> None:
    if silent_enabled():
        return

    if _active_deployment_display is not None and live_enabled():
        _active_deployment_display.set_system(system_label, "done", message)
        _active_deployment_display.add_event(f"{system_label}: {message}")
        return

    success(f"{system_label}: {message}")


def rsync_failure(system_label: str, message: str) -> None:
    if silent_enabled():
        return

    if _active_deployment_display is not None and live_enabled():
        _active_deployment_display.set_system(system_label, "failed", message)
        _active_deployment_display.set_stage("rsync", "failed", message)
        return

    failure(f"{system_label}: {message}")


def finish_rsync() -> None:
    if silent_enabled():
        return

    if _active_deployment_display is not None and live_enabled():
        _active_deployment_display.set_stage("rsync", "done", "all systems synced")
        return

    success("Rsync complete")


def start_process_assignment(system_labels: Sequence[str]) -> None:
    if silent_enabled():
        return

    if _active_deployment_display is not None and live_enabled():
        display = _active_deployment_display
        for label in system_labels:
            display.system_rows.setdefault(label, ("waiting", "waiting"))
        display.set_stage("processes", "running", "assigning process sets")
        return

    if live_enabled():
        display = LiveDeploymentDisplay("DEPLOYMENT")
        set_deployment_display(display)
        for label in system_labels:
            display.system_rows[label] = ("waiting", "waiting")
        display.set_stage("processes", "running", "assigning process sets")
        return

    section("Processes")
    detail("systems", len(system_labels))


def process_assignment(system_label: str, process_names: Sequence[str]) -> None:
    if silent_enabled():
        return

    message = ", ".join(process_names) if process_names else "no processes"
    if _active_deployment_display is not None and live_enabled():
        _active_deployment_display.set_system(system_label, "running", message)
        _active_deployment_display.add_event(f"{system_label}: {message}")
        return

    step(f"{system_label}: {message}")


def process_assignment_success(system_label: str) -> None:
    if silent_enabled():
        return

    if _active_deployment_display is not None and live_enabled():
        _active_deployment_display.set_system(system_label, "done", "processes set")
        _active_deployment_display.add_event(f"{system_label}: processes set")
        return

    success(f"{system_label}: processes set")


def process_assignment_failure(system_label: str) -> None:
    if silent_enabled():
        return

    if _active_deployment_display is not None and live_enabled():
        _active_deployment_display.set_system(
            system_label,
            "failed",
            "failed to set processes",
        )
        _active_deployment_display.set_stage(
            "processes",
            "failed",
            "failed to set processes",
        )
        return

    failure(f"{system_label}: failed to set processes")


def finish_process_assignment() -> None:
    if silent_enabled():
        return

    if _active_deployment_display is not None and live_enabled():
        _active_deployment_display.set_stage(
            "processes",
            "done",
            "all process sets applied",
        )
        _active_deployment_display.finish("deployment complete")
        return

    success("Process assignment complete")


def _context_prefix() -> str:
    return "| " if _context else ""


def _print(message: str = "") -> None:
    if message:
        print(f"{_context_prefix()}{message}")
        return

    print("|" if _context else "")


def log(message: object = "") -> None:
    if silent_enabled():
        return

    _print(str(message) if message is not None else "")


def bundle_header(title: str) -> None:
    print()
    print(_cyan(_box_border()))
    print(_cyan(f"| {_fit_box_line(f'BUNDLE {title}')} |"))
    print(_cyan(_box_border()))


def bundle_footer() -> None:
    print(_cyan(_box_border()))


def section(title: str) -> None:
    if silent_enabled():
        return

    if live_enabled() and _active_display is not None:
        return

    _print()
    _print(_cyan(f"-- {title} --"))


def step(message: str) -> None:
    if silent_enabled():
        return

    if live_enabled() and _active_display is not None:
        if _current_module_index is not None:
            _active_display.set_module_step(_current_module_index, message)
        else:
            _active_display.set_archive_step(message)
        return

    _print(f"{INDENT}{_cyan('>')} {message}")


def success(message: str) -> None:
    if silent_enabled():
        return

    if live_enabled() and _active_display is not None:
        return

    _print(f"{INDENT}{_green('OK')} {message}")


def failure(message: str) -> None:
    if silent_enabled():
        return

    if live_enabled() and _active_display is not None:
        if _current_module_index is not None:
            _active_display.fail_module(_current_module_index, message)
        else:
            _active_display.set_archive_step(message)

    _print(f"{INDENT}{_red('FAIL')} {message}")


def warning(message: str) -> None:
    if silent_enabled():
        return

    if live_enabled() and _active_display is not None:
        return

    _print(f"{INDENT}{_yellow('WARN')} {message}")


def detail(label: str, value: object) -> None:
    if silent_enabled():
        return

    if live_enabled() and _active_display is not None:
        if label == "result path" and _current_module_index is not None:
            _active_display.set_module_step(
                _current_module_index,
                f"compiled -> {value}",
            )
        return

    _print(f"{OUTPUT_INDENT}{label}: {value}")


def command_output(output: str) -> None:
    if silent_enabled():
        return

    if live_enabled() and _active_display is not None:
        add_current_console_line(output)
        return

    if live_enabled() and _active_deployment_display is not None:
        for line in output.splitlines():
            _active_deployment_display.add_event(strip_ansi(line))
        return

    if plain_enabled() and not _verbose_enabled():
        return

    for line in output.splitlines():
        _print(f"{OUTPUT_INDENT}{strip_ansi(line)}")


def command_failure(label: str, tail_lines: list[str]) -> None:
    failure(f"{label} failed")
    if not tail_lines:
        return

    detail("last output lines", "")
    for line in tail_lines:
        command_output(line)


def _fallback_logger_print(function_name: str, args: tuple[object, ...]) -> None:
    if silent_enabled():
        return

    if function_name == "detail" and len(args) >= 2:
        print(f"{OUTPUT_INDENT}{args[0]}: {args[1]}")
        return

    if function_name == "start_module" and len(args) >= 4:
        print(f"[{args[0]}/{args[1]}] {args[2]} ({args[3]})")
        return

    if function_name == "command_failure" and len(args) >= 2:
        print(f"{args[0]} failed")
        tail_lines = args[1]
        if isinstance(tail_lines, Sequence) and not isinstance(tail_lines, str):
            for line in tail_lines:
                print(line)
        return

    if args:
        print(args[0])


def _safe_logger(function: Callable[..., object]) -> Callable[..., object]:
    def wrapper(*args: object, **kwargs: object) -> object | None:
        global _logger_failed
        if _logger_failed:
            _fallback_logger_print(function.__name__, args)
            return None

        try:
            return function(*args, **kwargs)
        except Exception:
            _logger_failed = True
            _fallback_logger_print(function.__name__, args)
            return None

    return wrapper


for _logger_function_name, _logger_function in (
    ("log", log),
    ("start_bundle", start_bundle),
    ("start_module", start_module),
    ("complete_module", complete_module),
    ("start_archive", start_archive),
    ("finish_bundle", finish_bundle),
    ("section", section),
    ("step", step),
    ("success", success),
    ("failure", failure),
    ("warning", warning),
    ("detail", detail),
    ("command_output", command_output),
    ("command_failure", command_failure),
    ("refresh_deployment_display", refresh_deployment_display),
    ("start_deployment", start_deployment),
    ("start_discovery", start_discovery),
    ("discovery_tick", discovery_tick),
    ("discovered_system", discovered_system),
    ("finish_discovery", finish_discovery),
    ("deployment_stage", deployment_stage),
    ("deployment_event", deployment_event),
    ("start_rsync", start_rsync),
    ("rsync_step", rsync_step),
    ("rsync_success", rsync_success),
    ("rsync_failure", rsync_failure),
    ("finish_rsync", finish_rsync),
    ("start_process_assignment", start_process_assignment),
    ("process_assignment", process_assignment),
    ("process_assignment_success", process_assignment_success),
    ("process_assignment_failure", process_assignment_failure),
    ("finish_process_assignment", finish_process_assignment),
):
    globals()[_logger_function_name] = _safe_logger(_logger_function)


def strip_ansi(value: str) -> str:
    return ANSI_ESCAPE_PATTERN.sub("", value)


def _verbose_enabled() -> bool:
    return os.environ.get("BLITZ_VERBOSE") == "1"


def _live_status_enabled() -> bool:
    return sys.stdout.isatty()


def _live_events_enabled() -> bool:
    return os.environ.get("BLITZ_LIVE_EVENTS") == "1" or _verbose_enabled()


def _format_status_line(line: str) -> str:
    clean_line = " ".join(strip_ansi(line).strip().split())
    status_width = min(STATUS_WIDTH, _box_inner_width() - 8)
    if len(clean_line) > status_width:
        clean_line = clean_line[: status_width - 3] + "..."
    return clean_line
