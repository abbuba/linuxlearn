import sys
import readline
import urllib.request
import json
import subprocess
import time
import os
import shlex

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich.text import Text
from rich.align import Align

from linuxlearn.config import (
    load_config,
    save_config,
    reset_config,
    DEFAULT_CONFIG,
)
from linuxlearn.llm import LLMClient
from linuxlearn.router import FastPathRouter
from linuxlearn.security import SecurityValidator
from linuxlearn.session import SessionManager
from linuxlearn.context import TerminalContext
from linuxlearn.filesystem import FilesystemGrounder
from linuxlearn.learning import COURSE_ONE


console = Console()

ONLINE_API_URL = "https://api.groq.com/openai/v1"
ONLINE_MODEL = "openai/gpt-oss-120b"
LOCAL_OLLAMA_URL = "http://localhost:11434"


# ============================================================
# UI
# ============================================================

def clear_screen():
    try:
        console.clear()
    except Exception:
        print(
            "\033[2J\033[H",
            end="",
            flush=True,
        )


def pause(seconds=0.15):
    time.sleep(seconds)


def render_header(
    subtitle="Terminal-Native Learning System",
):
    clear_screen()

    header_panel = Panel(
        Text(
            f"LINUXLEARN  │  {subtitle}",
            justify="center",
            style="bold white",
        ),
        style="bold cyan",
        expand=False,
        padding=(0, 2),
    )

    console.print(
        Align.center(header_panel)
    )
    console.print()


def render_status(
    message,
    duration=0.35,
):
    with console.status(
        f"[bold yellow]{message}[/bold yellow]",
        spinner="dots",
    ):
        time.sleep(duration)


# ============================================================
# MODEL DETECTION
# ============================================================

def fetch_local_ollama_models():
    try:
        url = (
            f"{LOCAL_OLLAMA_URL}/api/tags"
        )

        request = urllib.request.Request(
            url,
            headers={
                "Content-Type":
                    "application/json"
            },
            method="GET",
        )

        with urllib.request.urlopen(
            request,
            timeout=2.5,
        ) as response:
            data = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

        return [
            model["name"]
            for model
            in data.get(
                "models",
                [],
            )
            if model.get("name")
        ]

    except Exception:
        return []


# ============================================================
# API KEY
# ============================================================

def get_validated_api_key():
    while True:
        console.print(
            "[dim]"
            "Paste your Cloud API key below "
            "(arrow keys & copy/paste enabled):"
            "[/dim]"
        )

        key = input(
            "  API Key: "
        ).strip()

        if key and key.lower() != "clear":
            return key

        console.print(
            "[bold red]"
            "⚠ API key cannot be blank. "
            "Please enter a valid key."
            "[/bold red]"
        )


# ============================================================
# LOCAL MODEL SELECTION
# ============================================================

def select_local_model(models):
    console.print()

    console.print(
        "[bold cyan]"
        "Select the local model LinuxLearn should use."
        "[/bold cyan]"
    )

    console.print()

    for index, model in enumerate(
        models,
        1,
    ):
        console.print(
            f"  [bold cyan][{index}][/bold cyan] "
            f"{model}"
        )

    console.print()

    while True:
        choice = input(
            "Select local model: "
        ).strip()

        if choice.isdigit():
            index = int(choice)

            if 1 <= index <= len(models):
                selected = models[
                    index - 1
                ]

                console.print(
                    f"\n[bold green]"
                    f"✓ Selected:"
                    f"[/bold green] "
                    f"{selected}"
                )

                return selected

        console.print(
            "[yellow]"
            "Invalid selection. "
            "Choose one of the numbers above."
            "[/yellow]"
        )


# ============================================================
# ONLINE CONFIG
# ============================================================

def show_online_defaults():
    console.print(
        Panel(
            "[bold cyan]"
            "LinuxLearn Online Mode"
            "[/bold cyan]\n\n"
            "LinuxLearn uses [bold]Groq[/bold] "
            "as its default online intelligence provider "
            "for fast terminal inference.\n\n"
            "[white]Default API URL:[/white]\n"
            f"[cyan]{ONLINE_API_URL}[/cyan]\n\n"
            "[white]Default model:[/white]\n"
            f"[cyan]{ONLINE_MODEL}[/cyan]\n\n"
            "[dim]"
            "These values are configured automatically. "
            "You can change the model later from Settings."
            "[/dim]",
            border_style="cyan",
            expand=False,
        )
    )

    console.print()


def configure_online(
    config,
    backup=False,
):
    if backup:
        console.print(
            "[bold yellow]"
            "Configuring Online Cloud API as Backup"
            "[/bold yellow]"
        )
    else:
        console.print(
            "[bold yellow]"
            "Step 2: Configuring Online Cloud API"
            "[/bold yellow]"
        )

    console.print()

    show_online_defaults()

    api_key = get_validated_api_key()

    if backup:
        config[
            "backup_provider"
        ] = "openai_compatible"

        config[
            "backup_api_base_url"
        ] = ONLINE_API_URL

        config[
            "backup_api_key"
        ] = api_key

        config[
            "backup_model"
        ] = ONLINE_MODEL

    else:
        config[
            "provider"
        ] = "openai_compatible"

        config[
            "api_base_url"
        ] = ONLINE_API_URL

        config[
            "api_key"
        ] = api_key

        config[
            "model"
        ] = ONLINE_MODEL

    render_status(
        "Configuring online intelligence layer...",
        duration=0.45,
    )

    console.print()

    if backup:
        console.print(
            "[bold green]"
            "✓ Online backup configured."
            "[/bold green]"
        )
    else:
        console.print(
            "[bold green]"
            "✓ Online backend configured."
            "[/bold green]"
        )


# ============================================================
# LOCAL CONFIG
# ============================================================

def configure_local(
    config,
    backup=False,
):
    if backup:
        console.print(
            "[bold yellow]"
            "Configuring Local Ollama as Backup"
            "[/bold yellow]"
        )
    else:
        console.print(
            "[bold yellow]"
            "Step 2: Inspecting Local Hardware & Runtimes"
            "[/bold yellow]"
        )

    console.print()

    console.print(
        "[dim]"
        f"LinuxLearn will look for Ollama at "
        f"{LOCAL_OLLAMA_URL}."
        "[/dim]"
    )

    console.print()

    render_status(
        "Scanning your machine for local Ollama instances...",
        duration=0.45,
    )

    models = fetch_local_ollama_models()

    if not models:
        console.print(
            "\n[bold red]"
            "✗ No local Ollama models were detected."
            "[/bold red]"
        )

        console.print(
            "[dim]"
            "Make sure Ollama is running and at least "
            "one model is installed."
            "[/dim]"
        )

        return False

    console.print(
        f"\n[bold green]"
        f"✓ Detected {len(models)} "
        f"local Ollama model(s)."
        f"[/bold green]"
    )

    selected = select_local_model(
        models
    )

    if backup:
        config[
            "backup_provider"
        ] = "ollama"

        config[
            "backup_ollama_base_url"
        ] = LOCAL_OLLAMA_URL

        config[
            "backup_model"
        ] = selected

    else:
        config[
            "provider"
        ] = "ollama"

        config[
            "ollama_base_url"
        ] = LOCAL_OLLAMA_URL

        config[
            "model"
        ] = selected

    return True


# ============================================================
# BACKUP FIELDS
# ============================================================

def initialize_backup_fields(
    config,
):
    config.setdefault(
        "backup_provider",
        None,
    )

    config.setdefault(
        "backup_model",
        "",
    )

    config.setdefault(
        "backup_api_base_url",
        "",
    )

    config.setdefault(
        "backup_api_key",
        "",
    )

    config.setdefault(
        "backup_ollama_base_url",
        LOCAL_OLLAMA_URL,
    )


# ============================================================
# ONBOARDING
# ============================================================

def onboarding_wizard():
    render_header(
        "Interactive Setup & Learning Onboarding"
    )

    manifesto = Panel(
        "[bold cyan]"
        "Why LinuxLearn?"
        "[/bold cyan]\n"
        "LinuxLearn keeps learning, explanation, and "
        "command execution inside the terminal.\n\n"
        "The system maintains terminal context so the assistant "
        "can understand where you are, what you just created, "
        "what commands succeeded, and what you are referring to.\n\n"
        "[dim]"
        "Let's configure your primary intelligence backend "
        "and optional backup."
        "[/dim]",
        border_style="cyan",
        expand=False,
    )

    console.print(
        Align.center(manifesto)
    )
    console.print()

    config = DEFAULT_CONFIG.copy()

    initialize_backup_fields(
        config
    )

    # --------------------------------------------------------
    # PRIMARY BACKEND
    # --------------------------------------------------------

    console.print(
        "[bold yellow]"
        "Step 1: Choosing Your Intelligence Backend"
        "[/bold yellow]"
    )

    console.print()

    console.print(
        "[white]"
        "Choose the backend LinuxLearn should use first. "
        "This becomes your primary backend."
        "[/white]"
    )

    console.print()

    table = Table(
        show_header=False,
        box=None,
        padding=(0, 1),
    )

    table.add_column(
        "Option",
        style="bold cyan",
    )

    table.add_column(
        "Backend",
        style="bold white",
    )

    table.add_column(
        "Description",
        style="dim",
    )

    table.add_row(
        "[1]",
        "Online Cloud API",
        "Fast cloud inference using Groq.",
    )

    table.add_row(
        "[2]",
        "Local Ollama",
        "Offline inference using a local model.",
    )

    console.print(table)
    console.print()

    choice = Prompt.ask(
        "Select primary backend",
        choices=["1", "2"],
        default="1",
    )

    # --------------------------------------------------------
    # ONLINE PRIMARY
    # --------------------------------------------------------

    if choice == "1":
        configure_online(
            config,
            backup=False,
        )

        console.print()

        console.print(
            "[bold cyan]"
            "Optional Backup Backend"
            "[/bold cyan]"
        )

        console.print(
            "[dim]"
            "You can configure Local Ollama as a backup. "
            "If the cloud backend becomes unavailable, "
            "LinuxLearn will be able to use the local backend."
            "[/dim]"
        )

        console.print()

        wants_backup = Confirm.ask(
            "Configure Local Ollama as backup?",
            default=False,
        )

        if wants_backup:
            configure_local(
                config,
                backup=True,
            )

    # --------------------------------------------------------
    # LOCAL PRIMARY
    # --------------------------------------------------------

    else:
        local_ok = configure_local(
            config,
            backup=False,
        )

        if not local_ok:
            console.print()

            console.print(
                "[bold yellow]"
                "Local Ollama is not ready."
                "[/bold yellow]"
            )

            console.print(
                "[dim]"
                "You can configure the Online Cloud API instead."
                "[/dim]"
            )

            console.print()

            wants_online = Confirm.ask(
                "Configure Online Cloud API now?",
                default=True,
            )

            if wants_online:
                configure_online(
                    config,
                    backup=False,
                )
            else:
                console.print(
                    "[bold red]"
                    "LinuxLearn needs a working primary "
                    "intelligence backend."
                    "[/bold red]"
                )

                input(
                    "\nPress Enter to exit..."
                )

                sys.exit(1)

        else:
            console.print()

            console.print(
                "[bold cyan]"
                "Optional Backup Backend"
                "[/bold cyan]"
            )

            console.print(
                "[dim]"
                "You can configure the Online Cloud API "
                "as a backup while keeping Ollama primary."
                "[/dim]"
            )

            console.print()

            wants_backup = Confirm.ask(
                "Configure Online Cloud API as backup?",
                default=False,
            )

            if wants_backup:
                configure_online(
                    config,
                    backup=True,
                )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    save_config(
        config
    )

    pause(
        0.2
    )

    primary_provider = config.get(
        "provider",
        "openai_compatible",
    )

    primary_model = config.get(
        "model",
        "",
    )

    backup_provider = config.get(
        "backup_provider"
    )

    if backup_provider == "ollama":
        backup_text = (
            "Local Ollama → "
            f"{config.get('backup_model', '')}"
        )
    elif backup_provider == "openai_compatible":
        backup_text = (
            "Online Cloud → "
            f"{config.get('backup_model', '')}"
        )
    else:
        backup_text = "Not configured"

    success_panel = Panel(
        "[bold green]"
        "✓ Setup Complete!"
        "[/bold green]\n\n"
        "Your LinuxLearn configuration has been saved safely to:\n"
        "[cyan]"
        "~/.config/linuxlearn/config.json"
        "[/cyan]\n\n"
        f"[white]Primary Backend:[/white] "
        f"{primary_provider}\n"
        f"[white]Primary Model:[/white] "
        f"{primary_model}\n"
        f"[white]Backup:[/white] "
        f"{backup_text}\n\n"
        "[dim]"
        "You can change the model or backend settings later "
        "from Main Menu → Settings."
        "[/dim]",
        border_style="green",
        expand=False,
    )

    console.print()

    console.print(
        Align.center(success_panel)
    )

    console.print()

    input(
        "Press Enter to launch LinuxLearn..."
    )

    return config


# ============================================================
# GLOBAL NAVIGATION
# ============================================================

def handle_global_nav(
    user_input,
    session=None,
):
    command = user_input.strip().lower()

    if command in {
        "exit",
        "quit",
    }:
        if session:
            try:
                json_file, md_file = (
                    session.export_notes()
                )

                if md_file:
                    console.print(
                        "\n[bold green]"
                        "✓ Session Study Notes Compiled:"
                        "[/bold green] "
                        f"{md_file}"
                    )

            except Exception as exc:
                console.print(
                    "[yellow]"
                    f"Could not export notes: {exc}"
                    "[/yellow]"
                )

        console.print(
            "[bold cyan]"
            "Exiting LinuxLearn. Keep building."
            "[/bold cyan]"
        )

        sys.exit(0)

    return command


# ============================================================
# CONTEXT DISPLAY
# ============================================================

def display_context(
    context: TerminalContext,
):
    console.print(
        "[dim]"
        "Current directory: "
        f"[cyan]{context.get_display_cwd()}[/cyan]"
        "[/dim]"
    )


# ============================================================
# PROPOSAL PATH NORMALIZATION
# ============================================================

def normalize_proposal_paths(
    context: TerminalContext,
    proposal: dict,
    key: str,
) -> list[str]:

    value = proposal.get(
        key,
        [],
    )

    if value is None:
        return []

    if isinstance(
        value,
        str,
    ):
        value = [value]

    if not isinstance(
        value,
        list,
    ):
        return []

    paths = []

    for item in value:
        if not isinstance(
            item,
            str,
        ):
            continue

        try:
            paths.append(
                str(
                    context.resolve_path(
                        item
                    )
                )
            )
        except Exception:
            continue

    return paths


# ============================================================
# EXECUTION
# ============================================================

def execute_command_streaming(
    command: str,
    context: TerminalContext,
    user_request: str,
    proposal: dict,
):
    """
    Execute using the context's current cwd and environment.

    Simple stateful commands such as cd/export/unset are handled
    directly by TerminalContext.

    Normal commands run in a subprocess whose cwd is controlled
    by TerminalContext.
    """

    if not command.strip():
        console.print(
            "[bold red]"
            "✗ Cannot execute an empty command."
            "[/bold red]"
        )
        return False

    # --------------------------------------------------------
    # SECURITY
    # --------------------------------------------------------

    try:
        blocked, reason = (
            SecurityValidator.is_blocked(
                command
            )
        )

        if blocked:
            console.print(
                "\n[bold red]"
                "🚨 SECURITY OVERRIDE:"
                "[/bold red] "
                f"{reason}"
            )

            return False

    except Exception as exc:
        console.print(
            "[bold red]"
            f"Security validation failed: {exc}"
            "[/bold red]"
        )

        return False

    # --------------------------------------------------------
    # INTERNAL STATEFUL COMMAND
    # --------------------------------------------------------

    internal = (
        context.handle_internal_command(
            command
        )
    )

    if internal is not None:
        if internal["success"]:

            console.print(
                "[dim]"
                "─── Terminal State Update ────────────────────"
                "[/dim]"
            )

            if internal["type"] == "cd":
                console.print(
                    "[bold green]"
                    f"✓ Current directory: "
                    f"{internal['current_cwd']}"
                    "[/bold green]"
                )

            elif internal["type"] == "export":
                console.print(
                    "[bold green]"
                    f"✓ Environment variable "
                    f"{internal['variable']} updated."
                    "[/bold green]"
                )

            elif internal["type"] == "unset":
                console.print(
                    "[bold green]"
                    f"✓ Environment variable "
                    f"{internal['variable']} removed."
                    "[/bold green]"
                )

            context.record_action(
                user_request=user_request,
                command=command,
                success=True,
                exit_code=0,
                duration_ms=0,
                cwd_before=internal.get(
                    "previous_cwd",
                    context.get_display_cwd(),
                ),
            )

            return True

        context.record_action(
            user_request=user_request,
            command=command,
            success=False,
            exit_code=1,
            duration_ms=0,
        )

        if internal["type"] == "cd":
            console.print(
                "[bold red]"
                "✗ Target directory does not exist."
                "[/bold red]"
            )

        return False

    # --------------------------------------------------------
    # NORMAL PROCESS EXECUTION
    # --------------------------------------------------------

    cwd_before = (
        context.get_display_cwd()
    )

    inferred = (
        context.infer_command_paths(
            command
        )
    )

    created_paths = (
        inferred["created_paths"]
    )

    modified_paths = (
        inferred["modified_paths"]
    )

    deleted_paths = (
        inferred["deleted_paths"]
    )

    # Add structured LLM metadata.
    for key, target_list in [
        (
            "created_paths",
            created_paths,
        ),
        (
            "modified_paths",
            modified_paths,
        ),
        (
            "deleted_paths",
            deleted_paths,
        ),
    ]:
        for path in normalize_proposal_paths(
            context,
            proposal,
            key,
        ):
            if path not in target_list:
                target_list.append(path)

    target_paths = normalize_proposal_paths(
        context,
        proposal,
        "target_paths",
    )

    started = time.monotonic()

    stdout_buffer = []
    stderr_buffer = []

    try:
        console.print(
            "[dim]"
            "─── Execution Start ───────────────────────────"
            "[/dim]"
        )

        console.print(
            "[dim]"
            f"Working directory: {cwd_before}"
            "[/dim]"
        )

        process = subprocess.Popen(
            [
                "bash",
                "-lc",
                command,
            ],
            cwd=str(
                context.cwd
            ),
            env=context.execution_env(),
            stdin=sys.stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        if process.stdout:
            for line in iter(
                process.stdout.readline,
                "",
            ):
                if not line:
                    break

                print(
                    line,
                    end="",
                    flush=True,
                )

                stdout_buffer.append(
                    line
                )

            process.stdout.close()

        return_code = process.wait()

        duration_ms = int(
            (
                time.monotonic()
                - started
            )
            * 1000
        )

        success = (
            return_code == 0
        )

        # ----------------------------------------------------
        # PERSIST CWD CHANGE
        # ----------------------------------------------------

        if success:
            changes_cwd = bool(
                proposal.get(
                    "changes_cwd",
                    False,
                )
            )

            working_directory = (
                proposal.get(
                    "working_directory"
                )
            )

            if changes_cwd and working_directory:
                resolved_cwd = context.resolve_path(
                    working_directory
                )

                if resolved_cwd.is_dir():
                    context.update_cwd(
                        str(
                            resolved_cwd
                        )
                    )

            # Also detect a simple leading cd
            # in compound commands such as:
            # cd ~/Desktop/ab && mkdir ...
            try:
                parts = shlex.split(
                    command
                )

                if (
                    len(parts) >= 2
                    and parts[0] == "cd"
                    and "&&" in parts
                ):
                    cd_index = parts.index(
                        "cd"
                    )

                    if (
                        cd_index == 0
                        and len(parts) > 1
                    ):
                        target = parts[1]

                        resolved = (
                            context.resolve_path(
                                target
                            )
                        )

                        if resolved.is_dir():
                            context.update_cwd(
                                str(
                                    resolved
                                )
                            )

            except Exception:
                pass

        stdout_text = "".join(
            stdout_buffer
        )

        stderr_text = "".join(
            stderr_buffer
        )

        context.record_action(
            user_request=user_request,
            command=command,
            success=success,
            exit_code=return_code,
            duration_ms=duration_ms,
            stdout=stdout_text,
            stderr=stderr_text,
            created_paths=created_paths,
            modified_paths=modified_paths,
            deleted_paths=deleted_paths,
            target_path=(
                target_paths[0]
                if target_paths
                else None
            ),
            cwd_before=cwd_before,
        )

        console.print(
            "\n[dim]"
            "─── Execution End ─────────────────────────────"
            "[/dim]"
        )

        if success:
            console.print(
                "[bold green]"
                "✓ Command completed successfully."
                "[/bold green]"
            )

            if created_paths:
                for path in created_paths[:5]:
                    console.print(
                        "[dim]"
                        f"Tracked created path: "
                        f"{path}"
                        "[/dim]"
                    )

            return True

        console.print(
            "[bold red]"
            f"✗ Command exited with status "
            f"{return_code}."
            "[/bold red]"
        )

        return False

    except KeyboardInterrupt:
        duration_ms = int(
            (
                time.monotonic()
                - started
            )
            * 1000
        )

        context.record_action(
            user_request=user_request,
            command=command,
            success=False,
            exit_code=None,
            duration_ms=duration_ms,
            stdout="",
            stderr="Interrupted by user.",
            cwd_before=cwd_before,
        )

        console.print(
            "\n[yellow]"
            "⚠ Execution interrupted by user."
            "[/yellow]"
        )

        return False

    except Exception as exc:
        duration_ms = int(
            (
                time.monotonic()
                - started
            )
            * 1000
        )

        context.record_action(
            user_request=user_request,
            command=command,
            success=False,
            exit_code=None,
            duration_ms=duration_ms,
            stderr=str(exc),
            cwd_before=cwd_before,
        )

        console.print(
            "\n[bold red]"
            f"Execution error: {exc}"
            "[/bold red]"
        )

        return False


# ============================================================
# FILESYSTEM GROUNDING
# ============================================================

def ground_proposal_targets(
    proposal: dict,
    filesystem: FilesystemGrounder,
) -> dict:
    """
    Ground the paths declared by a command proposal against the
    real filesystem.
    This does not execute anything.
    """
    target_paths = proposal.get("target_paths") or []
    if isinstance(target_paths, str):
        target_paths = [target_paths]

    grounded_targets = []
    for target in target_paths:
        if not target:
            continue
        try:
            result = filesystem.ground(target)
            grounded_targets.append(result.to_dict())
        except Exception as exc:
            grounded_targets.append(
                {
                    "requested": str(target),
                    "resolved_path": None,
                    "exists": False,
                    "kind": "error",
                    "confidence": "none",
                    "reason": (
                        f"Filesystem grounding failed: {exc}"
                    ),
                }
            )

    proposal["grounded_targets"] = grounded_targets
    return proposal


def validate_proposal_against_filesystem(
    proposal: dict,
    filesystem: FilesystemGrounder,
) -> tuple[bool, str]:
    """
    Perform a conservative filesystem grounding check.
    This is NOT the security validator.
    SecurityValidator answers:
        "Is this command dangerous or blocked?"
    FilesystemGrounder answers:
        "Does the target actually exist or make sense?"
    """
    command = str(proposal.get("command", "")).strip()
    if not command:
        return False, "The proposal contains no command."

    intent = str(proposal.get("intent", "")).lower().strip()
    target_paths = proposal.get("target_paths") or []
    if isinstance(target_paths, str):
        target_paths = [target_paths]

    existing_target_operations = {
        "delete",
        "remove",
        "open",
        "read",
        "cd",
        "enter",
        "go",
        "copy",
        "move",
        "rename",
    }

    if intent in existing_target_operations:
        if not target_paths:
            return True, ""
        for target in target_paths:
            if not target:
                continue
            result = filesystem.ground(
                target,
                search_if_missing=False,
            )
            if not result.exists:
                return (
                    False,
                    f"Target does not exist: {target}",
                )
            if result.confidence == "low":
                return False, result.reason

    return True, ""


# ============================================================
# DISCOVERY MODE
# ============================================================

def discovery_mode(
    config,
    session,
    context: TerminalContext,
    filesystem: FilesystemGrounder | None = None,
):
    if filesystem is None:
        filesystem = FilesystemGrounder(context)

    client = LLMClient(
        config,
        context,
    )

    render_header(
        "Discovery Mode"
    )

    console.print(
        Panel(
            "[bold cyan]"
            "Discovery Mode"
            "[/bold cyan]\n\n"
            "Describe what you want to accomplish "
            "in normal English.\n"
            "LinuxLearn keeps track of your terminal state, "
            "recent actions, known files and folders, "
            "and the current working directory.\n\n"
            "[dim]"
            "Commands: back → Main Menu | "
            "exit → Quit & save session"
            "[/dim]",
            border_style="cyan",
            expand=False,
        )
    )

    console.print()

    display_context(
        context
    )

    console.print()

    while True:
        user_input = input(
            "linuxlearn> "
        ).strip()

        if not user_input:
            continue

        nav = handle_global_nav(
            user_input,
            session,
        )

        if nav == "back":
            break

        # ----------------------------------------------------
        # FAST PATH FIRST
        # ----------------------------------------------------

        proposal = FastPathRouter.match(
            user_input,
            context,
        )

        if proposal:
            source_badge = (
                "[bold yellow]"
                "⚡ FAST PATH"
                "[/bold yellow]"
            )

            proposal.setdefault(
                "source",
                "fast_path",
            )

        # ----------------------------------------------------
        # CONTEXT-AWARE LLM
        # ----------------------------------------------------

        else:
            render_status(
                "Reading terminal context and synthesizing command...",
                duration=0.35,
            )

            try:
                proposal, engine_badge = (
                    client.query(
                        user_input
                    )
                )

                proposal["source"] = "llm"

                source_badge = (
                    "[bold magenta]"
                    "🧠 LLM GENERATED "
                    f"({engine_badge})"
                    "[/bold magenta]"
                )

            except Exception as exc:
                console.print(
                    "\n[bold red]"
                    f"Inference Error: {exc}"
                    "[/bold red]"
                )

                continue

        proposal = ground_proposal_targets(
            proposal,
            filesystem,
        )

        grounded_ok, grounding_reason = (
            validate_proposal_against_filesystem(
                proposal,
                filesystem,
            )
        )

        if not grounded_ok:
            console.print(
                "\n[bold yellow]"
                "⚠ Filesystem Grounding Check"
                "[/bold yellow]"
            )
            console.print(
                f"[yellow]{grounding_reason}[/yellow]"
            )
            console.print(
                "[dim]LinuxLearn will not execute this proposal blindly.[/dim]"
            )
            console.print()
            continue

        # ----------------------------------------------------
        # COMMAND DATA
        # ----------------------------------------------------

        command = proposal.get(
            "command",
            "",
        )

        explanation = proposal.get(
            "explanation",
            "",
        )

        concept = proposal.get(
            "concept",
            "General Linux",
        )

        risk = str(
            proposal.get(
                "risk",
                "low",
            )
        ).upper()

        requires_sudo = bool(
            proposal.get(
                "requires_sudo",
                False,
            )
        )

        # ----------------------------------------------------
        # SECURITY CHECK
        # ----------------------------------------------------

        blocked, reason = (
            SecurityValidator.is_blocked(
                command
            )
        )

        if blocked:
            console.print(
                "\n[bold red]"
                "🚨 SECURITY OVERRIDE:"
                "[/bold red] "
                f"{reason}"
            )

            continue

        # ----------------------------------------------------
        # DISPLAY
        # ----------------------------------------------------

        syntax = Syntax(
            command,
            "bash",
            line_numbers=False,
        )

        console.print()

        console.print(
            Panel(
                syntax,
                title=(
                    "Suggested Command │ "
                    f"{source_badge}"
                ),
                border_style="green",
            )
        )

        console.print()

        console.print(
            "[bold white]"
            "English Request:"
            "[/bold white] "
            f"{user_input}"
        )

        console.print(
            "[bold white]"
            "What this command does:"
            "[/bold white] "
            f"{explanation}"
        )

        console.print(
            "[bold white]"
            "Core Concept:"
            "[/bold white] "
            f"[cyan]{concept}[/cyan]"
        )

        console.print(
            "[bold white]"
            "Risk:"
            "[/bold white] "
            f"{risk}   │   "
            "[bold white]"
            "Sudo:"
            "[/bold white] "
            f"{'YES' if requires_sudo else 'NO'}"
        )

        grounded_targets = proposal.get(
            "grounded_targets",
            [],
        )
        if grounded_targets:
            console.print()
            console.print(
                "[bold cyan]Filesystem Grounding[/bold cyan]"
            )
            for target in grounded_targets:
                requested = target.get("requested", "")
                resolved = target.get("resolved_path")
                exists = target.get("exists", False)
                confidence = target.get("confidence", "none")
                if exists and resolved:
                    console.print(
                        f"  [green]✓[/green] "
                        f"{requested} → {resolved} "
                        f"[dim]({confidence})[/dim]"
                    )
                else:
                    console.print(
                        f"  [yellow]⚠[/yellow] "
                        f"{requested} → "
                        f"{target.get('reason', 'Not found')}"
                    )

        console.print(
            "[bold white]"
            "Terminal Context:"
            "[/bold white] "
            f"[cyan]"
            f"{context.get_display_cwd()}"
            "[/cyan]"
        )

        # Show resolved references when relevant.
        references = (
            context.resolve_references(
                user_input
            )
        )

        resolved = references.get(
            "resolved",
            [],
        )

        if resolved:
            console.print()

            console.print(
                "[bold white]"
                "Resolved Context:"
                "[/bold white]"
            )

            for item in resolved[:5]:
                console.print(
                    f"  [cyan]"
                    f"{item['reference']}"
                    f"[/cyan] → "
                    f"{item['path']}"
                )

        console.print()

        # ----------------------------------------------------
        # APPROVAL
        # ----------------------------------------------------

        execute_input = input(
            "Execute command on host? "
            "[y/N/back/exit]: "
        ).strip()

        nav = handle_global_nav(
            execute_input,
            session,
        )

        if nav == "back":
            continue

        if nav == "y":
            pause(
                0.1
            )

            cwd_before = (
                context.get_display_cwd()
            )

            success = (
                execute_command_streaming(
                    command,
                    context,
                    user_input,
                    proposal,
                )
            )

            # Add context metadata to the session event.
            session_proposal = dict(
                proposal
            )

            session_proposal[
                "context_before"
            ] = {
                "cwd":
                    cwd_before,
                "resolved_references":
                    references,
            }

            session_proposal[
                "context_after"
            ] = {
                "cwd":
                    context.get_display_cwd(),
                "last_created_path":
                    (
                        str(
                            context.last_created_path
                        )
                        if context.last_created_path
                        else None
                    ),
                "last_target_path":
                    (
                        str(
                            context.last_target_path
                        )
                        if context.last_target_path
                        else None
                    ),
            }

            if success:
                console.print(
                    f"[bold green]"
                    f"✓ Success. "
                    f"Concept logged: "
                    f"{concept}"
                    f"[/bold green]"
                )

                if success:
                    for path in proposal.get("created_paths", []) or []:
                        try:
                            context.register_path(path, source_command="post_execution_grounding")
                        except Exception:
                            pass

                    target_paths = proposal.get("target_paths") or []
                    if isinstance(target_paths, str):
                        target_paths = [target_paths]
                    refreshed_grounding = filesystem.ground_many(target_paths)
                    proposal["post_execution_grounding"] = [
                        item.to_dict() for item in refreshed_grounding
                    ]
            else:
                console.print(
                    "[bold red]"
                    "✗ Execution returned a non-zero status."
                    "[/bold red]"
                )

            session.record(
                user_input,
                session_proposal,
                executed=True,
                success=success,
            )

        else:
            console.print(
                "[dim]"
                "Command not executed. "
                "Returning to Discovery prompt..."
                "[/dim]"
            )

            session.record(
                user_input,
                proposal,
                executed=False,
                success=False,
            )

        console.print()

        display_context(
            context
        )

        console.print()


# ============================================================
# SETTINGS
# ============================================================

def settings_panel(
    config,
    session,
):
    render_header(
        "Configuration Management"
    )

    initialize_backup_fields(
        config
    )

    table = Table(
        show_header=True,
        header_style="bold magenta",
        expand=True,
    )

    table.add_column(
        "Key",
        style="bold yellow",
        width=6,
    )

    table.add_column(
        "Parameter",
        style="bold white",
        width=28,
    )

    table.add_column(
        "Active Value",
        style="green",
    )

    table.add_row(
        "1",
        "Primary Backend",
        config.get(
            "provider",
            "openai_compatible",
        ),
    )

    table.add_row(
        "2",
        "Primary Model",
        config.get(
            "model",
            "",
        ),
    )

    backup_provider = config.get(
        "backup_provider"
    )

    if backup_provider:
        backup_text = (
            f"{backup_provider} → "
            f"{config.get('backup_model', '')}"
        )
    else:
        backup_text = "Not configured"

    table.add_row(
        "3",
        "Backup Backend",
        backup_text,
    )

    table.add_row(
        "4",
        "Configure / Change Backup",
        "Optional",
    )

    table.add_row(
        "5",
        "API Key",
        (
            "Configured"
            if config.get(
                "api_key"
            )
            else "[dim]Not Set[/dim]"
        ),
    )

    table.add_row(
        "6",
        "Factory Reset",
        "[red]"
        "Wipe config & re-run setup"
        "[/red]",
    )

    console.print(
        Panel(
            table,
            border_style="magenta",
        )
    )

    console.print()

    console.print(
        "[yellow][1][/yellow] Backend  │  "
        "[yellow][2][/yellow] Model  │  "
        "[yellow][3-4][/yellow] Backup  │  "
        "[yellow][5][/yellow] API Key  │  "
        "[yellow][6][/yellow] Reset  │  "
        "[yellow]back[/yellow] Return\n"
    )

    while True:
        choice = input(
            "> "
        ).strip()

        nav = handle_global_nav(
            choice,
            session,
        )

        if nav == "back":
            break

        if nav == "1":
            config["provider"] = Prompt.ask(
                "Select primary backend",
                choices=[
                    "openai_compatible",
                    "ollama",
                ],
                default=config.get(
                    "provider",
                    "openai_compatible",
                ),
            )

            if config["provider"] == "openai_compatible":
                config[
                    "api_base_url"
                ] = ONLINE_API_URL

                if not config.get(
                    "api_key"
                ):
                    config[
                        "api_key"
                    ] = (
                        get_validated_api_key()
                    )

                if not config.get(
                    "model"
                ):
                    config[
                        "model"
                    ] = ONLINE_MODEL

            else:
                config[
                    "ollama_base_url"
                ] = LOCAL_OLLAMA_URL

                models = (
                    fetch_local_ollama_models()
                )

                if models:
                    config["model"] = (
                        select_local_model(
                            models
                        )
                    )

            save_config(
                config
            )

            console.print(
                "[bold green]"
                "✓ Primary backend saved."
                "[/bold green]"
            )

        elif nav == "2":
            if config.get(
                "provider"
            ) == "ollama":

                models = (
                    fetch_local_ollama_models()
                )

                if models:
                    config["model"] = (
                        select_local_model(
                            models
                        )
                    )
                else:
                    console.print(
                        "[yellow]"
                        "No local Ollama models detected."
                        "[/yellow]"
                    )

            else:
                console.print(
                    f"[dim]"
                    f"Current online model: "
                    f"{config.get('model', ONLINE_MODEL)}"
                    f"[/dim]"
                )

                new_model = input(
                    "Enter new online model name: "
                ).strip()

                if new_model:
                    config[
                        "model"
                    ] = new_model

            save_config(
                config
            )

        elif nav == "3":
            if backup_provider:
                console.print(
                    "[dim]"
                    f"Backup: "
                    f"{backup_provider} → "
                    f"{config.get('backup_model', '')}"
                    "[/dim]"
                )
            else:
                console.print(
                    "[dim]"
                    "No backup configured."
                    "[/dim]"
                )

        elif nav == "4":
            primary = config.get(
                "provider",
                "openai_compatible",
            )

            if primary == "openai_compatible":
                configure_local(
                    config,
                    backup=True,
                )
            else:
                configure_online(
                    config,
                    backup=True,
                )

            save_config(
                config
            )

        elif nav == "5":
            config[
                "api_key"
            ] = get_validated_api_key()

            save_config(
                config
            )

            console.print(
                "[bold green]"
                "✓ API key saved."
                "[/bold green]"
            )

        elif nav == "6":
            if Confirm.ask(
                "\n[bold red]"
                "Factory reset all settings?"
                "[/bold red]"
            ):
                reset_config()

                console.print(
                    "[bold green]"
                    "Settings wiped. "
                    "Restarting setup..."
                    "[/bold green]"
                )

                return onboarding_wizard()

        else:
            console.print(
                "[yellow]"
                "Invalid option."
                "[/yellow]"
            )


# ============================================================
# MAIN
# ============================================================

def _record_learning_event(session, label, command="", success=True, explanation=""):
    """Include course activity in the existing session export."""
    session.record(
        user_prompt=f"Learn: {label}",
        proposal={
            "command": command,
            "explanation": explanation,
            "concept": "LinuxLearn Course 1",
        },
        executed=bool(command),
        success=success,
    )


def _lesson_example_matches(example, record, cwd_before, context, relative_target=None):
    """Check a learner's real command result against this lesson objective."""
    if record is None or not record.success:
        return False

    expected = example["command"]
    actual = record.command.strip()
    if expected == 'echo "Hello Linux"':
        return actual in {'echo "Hello Linux"', "echo 'Hello Linux'"} and "Hello Linux" in record.stdout
    if expected == "pwd":
        return actual == "pwd" and bool(record.stdout.strip())
    if expected == "ls":
        return actual == "ls"
    if expected == "ls -la":
        return actual == "ls -la"
    if expected == "cd <directory>":
        return actual.startswith("cd ") and record.cwd_after != cwd_before
    if expected == "cd ..":
        return actual == "cd .." and record.cwd_after != cwd_before
    if expected == "cd ~":
        return actual == "cd ~" and context.cwd == context.home
    if expected == "cd <path>":
        return actual.startswith("cd ") and record.cwd_after != cwd_before
    if expected == "cd <relative path>":
        try:
            parts = shlex.split(actual)
            return (
                len(parts) == 2
                and not os.path.isabs(os.path.expanduser(parts[1]))
                and parts[1] != "~"
                and record.cwd_after != cwd_before
            )
        except ValueError:
            return False
    if expected == "cd <absolute path>":
        try:
            parts = shlex.split(actual)
            return (
                len(parts) == 2
                and os.path.isabs(os.path.expanduser(parts[1]))
                and relative_target is not None
                and context.cwd == relative_target
            )
        except ValueError:
            return False
    return False


def _run_course_command(context, session, command, label):
    history_length = len(context.command_history)
    ok = execute_command_streaming(
        command,
        context,
        user_request=f"Learn: {label}",
        proposal={},
    )
    record = context.command_history[-1] if len(context.command_history) > history_length else None
    _record_learning_event(session, label, command, ok)
    return ok, record


def _run_course_lesson(lesson, context, session, lesson_number):
    render_header(f"Basic · Course 1 · Lesson {lesson_number}")
    console.print(f"[bold cyan]{lesson['title']}[/bold cyan]\n")
    console.print(lesson["explanation"])
    console.print("\n[dim]Type :back to return to the course menu.[/dim]\n")

    relative_target = None
    for example in lesson["examples"]:
        if lesson["title"] == "Moving Around" and example["command"] == "cd <directory>":
            directories = [
                entry["name"]
                for entry in context.filesystem.snapshot()
                if entry.get("kind") == "directory" and entry.get("name") not in {".", ".."}
            ]
            if directories:
                console.print("[dim]Directories you can enter here: " + ", ".join(shlex.quote(name) for name in directories) + "[/dim]")
        command_hint = example["command"]
        if "<directory>" in command_hint:
            command_hint = "cd <directory-name>"
        elif command_hint == "cd <relative path>":
            command_hint = "cd <directory-name>"
        elif command_hint == "cd <absolute path>" and relative_target is not None:
            command_hint = f"cd {relative_target}"
        elif "<path>" in command_hint:
            command_hint = "cd <relative-or-absolute-path>"
        console.print(f"[bold]Try:[/bold] [green]{command_hint}[/green]")
        while True:
            command = input("$ ").strip()
            if command.lower() in {":back", "back"}:
                _record_learning_event(session, f"Lesson {lesson_number} left before completion", success=False)
                return False
            cwd_before = context.get_display_cwd()
            ok, record = _run_course_command(context, session, command, f"Lesson {lesson_number}: {lesson['title']}")
            if _lesson_example_matches(example, record, cwd_before, context, relative_target):
                if example["command"] == "cd <relative path>":
                    relative_target = context.cwd
                console.print(f"\n[dim]{example['why']}[/dim]")
                after = example["after"].format(cwd=context.get_display_cwd())
                console.print(f"[dim]{after}[/dim]\n")
                break
            if not ok:
                console.print("[yellow]Try again after checking the command and your current directory.[/yellow]")
            else:
                console.print("[yellow]That ran successfully. Try the command shown for this step so we can observe this concept.[/yellow]")

    _record_learning_event(session, f"Lesson {lesson_number} completed")
    console.print("[bold green]Lesson complete.[/bold green]")
    input("Press Enter to continue...")
    return True


def _run_course_challenge(context, session):
    render_header("Basic · Course 1 · Final Challenge")
    console.print("[bold cyan]Your challenge[/bold cyan]\n")
    console.print("Navigate to your home directory, find a directory you can enter, enter it, and prove where you are.")
    console.print("Use `pwd`, `ls`, and `cd` as needed. The goal is to finish inside a real directory below your home directory.")
    console.print("\n[dim]Type :back to leave the challenge. Your progress will remain incomplete.[/dim]\n")

    history_start = len(context.command_history)
    start_cwd = context.cwd
    visited_home = start_cwd == context.home
    while True:
        command = input("$ ").strip()
        if command.lower() in {":back", "back"}:
            _record_learning_event(session, "Final challenge left incomplete", success=False)
            return False
        _run_course_command(context, session, command, "Course 1 final challenge")
        if context.cwd == context.home:
            visited_home = True
        try:
            below_home = context.cwd != context.home and context.cwd.is_relative_to(context.home) and context.cwd.is_dir()
        except AttributeError:
            below_home = context.cwd != context.home and context.home in context.cwd.parents and context.cwd.is_dir()
        recent = context.command_history[history_start:]
        navigated_into_directory = any(
            item.success and item.cwd_after == context.get_display_cwd() and item.cwd_before != item.cwd_after
            for item in recent
        )
        proved_location = any(
            item.success
            and item.command.strip() == "pwd"
            and item.cwd_after == context.get_display_cwd()
            and bool(item.stdout.strip())
            for item in recent
        )
        if visited_home and below_home and navigated_into_directory and proved_location:
            console.print(f"\n[bold green]Challenge complete.[/bold green] You are in {context.get_display_cwd()}.")
            _record_learning_event(session, "Final challenge completed", command, success=True, explanation=f"Verified current directory: {context.cwd}")
            return True
        console.print(f"[dim]Current directory: {context.get_display_cwd()}[/dim]")


def learn_mode(context, session):
    while True:
        render_header("Learn")
        console.print("[bold cyan]Choose a level[/bold cyan]\n")
        console.print("[1] Basic\n[2] Intermediate (coming later)\n[3] Advanced (coming later)\n[0] Back\n")
        choice = input("> ").strip().lower()
        if choice in {"0", "back"}:
            return
        if choice == "1":
            while True:
                render_header("Learn · Basic")
                console.print("[bold cyan]Basic courses[/bold cyan]\n")
                console.print("[1] Getting Comfortable with Linux")
                console.print("[0] Back\n")
                course_choice = input("> ").strip().lower()
                if course_choice in {"0", "back"}:
                    break
                if course_choice != "1":
                    console.print("[yellow]Choose Course 1 or 0.[/yellow]")
                    pause(0.3)
                    continue
                completed_lessons = set()
                challenge_complete = False
                while True:
                    render_header("Learn · Basic · Course 1")
                    console.print(f"[bold cyan]{COURSE_ONE['title']}[/bold cyan]\n")
                    for index, lesson in enumerate(COURSE_ONE["lessons"], 1):
                        mark = "✓" if index in completed_lessons else " "
                        console.print(f"[{index}] [{mark}] Lesson {index} — {lesson['title']}")
                    challenge_mark = "✓" if challenge_complete else " "
                    console.print(f"[6] [{challenge_mark}] Final challenge\n[0] Back\n")
                    selection = input("> ").strip().lower()
                    if selection in {"0", "back"}:
                        break
                    if selection.isdigit() and 1 <= int(selection) <= 5:
                        number = int(selection)
                        if _run_course_lesson(COURSE_ONE["lessons"][number - 1], context, session, number):
                            completed_lessons.add(number)
                        continue
                    if selection == "6":
                        if len(completed_lessons) < len(COURSE_ONE["lessons"]):
                            console.print("[yellow]Complete all five lessons before the final challenge.[/yellow]")
                            input("Press Enter to continue...")
                            continue
                        challenge_complete = _run_course_challenge(context, session)
                        if challenge_complete:
                            _record_learning_event(session, "Course 1 completed", success=True)
                            console.print("[bold green]Course 1 complete. Your completion is included in this session's study notes.[/bold green]")
                            input("Press Enter to continue...")
                        continue
                    console.print("[yellow]Choose a lesson, 6, or 0.[/yellow]")
                    pause(0.3)
        elif choice in {"2", "3"}:
            render_header("Learn")
            console.print("[yellow]This learning level is not available yet.[/yellow]")
            input("Press Enter to return...")
        else:
            console.print("[yellow]Choose Basic, Intermediate, Advanced, or 0.[/yellow]")
            pause(0.3)

def main():
    config = load_config()

    if not config:
        config = onboarding_wizard()

    initialize_backup_fields(
        config
    )

    # ========================================================
    # ONE CONTEXT FOR THE WHOLE SESSION
    # ========================================================

    context = TerminalContext()
    filesystem = FilesystemGrounder(context)

    session = SessionManager()

    while True:
        render_header(
            "Main Menu (🔴 Session Active)"
        )

        display_context(
            context
        )

        console.print()

        table = Table(
            show_header=False,
            box=None,
        )

        table.add_column(
            "Option",
            style="bold yellow",
        )

        table.add_column(
            "Mode",
            style="bold white",
        )

        table.add_row(
            "[1]",
            "Discovery Mode (Context-Aware)",
        )

        table.add_row(
            "[2]",
            "Learn Mode (Phase 5)",
        )

        table.add_row(
            "[3]",
            "Settings & Provider Management",
        )

        console.print(
            table
        )

        console.print(
            "\nType [yellow]exit[/yellow] "
            "to quit, compile notes, and export the session.\n"
        )

        choice = input(
            "> "
        ).strip()

        nav = handle_global_nav(
            choice,
            session,
        )

        if nav == "1":
            discovery_mode(
                config,
                session,
                context,
                filesystem,
            )

        elif nav == "2":
            learn_mode(context, session)

        elif nav == "3":
            updated = settings_panel(
                config,
                session,
            )

            if updated:
                config = updated

        else:
            console.print(
                "[yellow]"
                "Invalid option. "
                "Please choose 1, 2, or 3."
                "[/yellow]"
            )

            pause(
                0.4
            )


if __name__ == "__main__":
    main()
