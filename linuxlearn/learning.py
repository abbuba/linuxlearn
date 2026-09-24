"""Interactive, terminal-native learning curriculum for LinuxLearn Course 1."""

from __future__ import annotations

import os
import shlex
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich.align import Align
from rich.box import ROUNDED, SIMPLE, SQUARE
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


# ============================================================
# PACING CONTROLLER
# ============================================================

class LearningPacing:
    """Centralized, configurable pacing controller for calm learning transitions.

    Can be adjusted or disabled via environment variables:
      LINUXLEARN_PACING=0 / off / false (disables pauses for fast navigation/testing)
      LINUXLEARN_PACING_SPEED=0.5 (scales pause durations)
    """

    def __init__(self, speed: float = 1.0, enabled: bool = True):
        env_val = os.getenv("LINUXLEARN_PACING", "1").strip().lower()
        if env_val in {"0", "false", "off", "no"}:
            self.enabled = False
        else:
            self.enabled = enabled

        try:
            self.speed = float(os.getenv("LINUXLEARN_PACING_SPEED", str(speed)))
        except ValueError:
            self.speed = speed

    def pause(self, seconds: float = 0.4):
        if not self.enabled or self.speed <= 0:
            return
        time.sleep(seconds * self.speed)

    def stage(self, stage_name: str = "default"):
        durations = {
            "after_input": 0.3,
            "after_output": 0.4,
            "after_explanation": 0.45,
            "after_breakdown": 0.45,
            "after_examples": 0.4,
            "after_recap": 0.35,
            "brief": 0.2,
            "default": 0.35,
        }
        duration = durations.get(stage_name, 0.35)
        self.pause(duration)


default_pacing = LearningPacing()


# ============================================================
# COURSE 1 CURRICULUM DATA
# ============================================================

COURSE_ONE: Dict[str, Any] = {
    "id": 1,
    "level": "Basic",
    "title": "Getting Comfortable with the Terminal",
    "description": "Master the Linux command line from scratch: shells, navigation, commands, and paths.",
    "lessons": [
        {
            "id": 1,
            "number": 1,
            "title": "Meet the Terminal",
            "concept": (
                "A terminal is the text-based interface where you communicate directly with "
                "your computer using typed commands instead of graphical clicks.\n\n"
                "Inside the terminal runs the [bold cyan]shell[/bold cyan]—a program that reads "
                "the commands you type, tells the Linux kernel what to execute, and prints the result.\n\n"
                "The [bold cyan]prompt[/bold cyan] (`$`) indicates that the shell is ready and waiting for your next command."
            ),
            "command_intro": "The `echo` command prints any text argument you provide back onto the terminal screen.",
            "steps": [
                {
                    "step_number": 1,
                    "prompt_hint": 'echo "Hello Linux"',
                    "expected_type": "echo_hello",
                    "instruction": "Print your first message to the terminal screen.",
                    "what_happened": (
                        "The shell received your line, recognized [bold cyan]echo[/bold cyan] as the executable command, "
                        "and passed [bold green]\"Hello Linux\"[/bold green] as its text argument. "
                        "`echo` printed that string directly to the terminal."
                    ),
                    "breakdown": {
                        "command": 'echo "Hello Linux"',
                        "parts": [
                            ("echo", "Command (Executable)", "The program that writes text to standard output."),
                            ('"Hello Linux"', "Argument (String)", "The text passed to echo. Quotes group words into one argument."),
                        ],
                        "why": "The shell parsed the command, executed the `echo` utility, and wrote the string followed by a newline.",
                    },
                    "examples": [
                        ('echo "My name is Abbu"', "Prints a personalized greeting"),
                        ('echo "Linux is running"', "Displays a status message"),
                        ('echo "Hello from the terminal"', "Passes arbitrary text to standard output"),
                    ],
                }
            ],
            "recap": [
                "The terminal is the text-based interface where you communicate with the shell.",
                "The shell reads your input, executes programs, and displays the output.",
                "The command prompt ($) indicates that the shell is ready for input.",
                "`echo` prints text arguments directly back to the terminal screen.",
            ],
        },
        {
            "id": 2,
            "number": 2,
            "title": "Where Am I?",
            "concept": (
                "In Linux, every terminal session is always located somewhere in the filesystem. "
                "This location is called your [bold cyan]Current Working Directory (CWD)[/bold cyan].\n\n"
                "Whenever you create files, search for directories, or run scripts, the shell "
                "uses this location as its starting reference point.\n\n"
                "Linux organizes all files and folders in a single hierarchical tree originating at root (`/`)."
            ),
            "command_intro": "The `pwd` command stands for [bold cyan]print working directory[/bold cyan]. It asks Linux to reveal your current location.",
            "steps": [
                {
                    "step_number": 1,
                    "prompt_hint": "pwd",
                    "expected_type": "pwd",
                    "instruction": "Ask Linux for the full path of your current working directory.",
                    "what_happened": (
                        "Linux inspected your active shell process and reported the full absolute path "
                        "of your current working directory: [bold cyan]{cwd}[/bold cyan]."
                    ),
                    "breakdown": {
                        "command": "pwd",
                        "parts": [
                            ("pwd", "Command (Builtin/Utility)", "Stands for 'print working directory'."),
                            ("(none)", "Arguments", "Requires no arguments; automatically inspects current process state."),
                        ],
                        "why": "Linux queries the operating system for the current working directory inode and prints its full path.",
                    },
                    "examples": [
                        ("pwd", "Prints your current absolute working directory"),
                        ("echo $PWD", "Reads the shell environment variable containing the active path"),
                    ],
                }
            ],
            "recap": [
                "The shell always operates inside a current working directory.",
                "`pwd` (print working directory) reveals your exact location in the filesystem.",
                "Linux paths use forward slashes (/) to separate directory names.",
                "Checking your location ensures commands run in the intended directory.",
            ],
        },
        {
            "id": 3,
            "number": 3,
            "title": "What Is Around Me?",
            "concept": (
                "Once you know where you are, you need to inspect what files and folders surround you.\n\n"
                "The [bold cyan]ls[/bold cyan] command lists the contents of a directory. By default, it displays visible files.\n\n"
                "Linux commands can be customized using [bold cyan]flags[/bold cyan] (options) starting with a dash (`-`). "
                "Flags instruct a command to change how it gathers or formats information."
            ),
            "command_intro": "First inspect visible files with `ls`, then inspect all items and metadata with `ls -la`.",
            "steps": [
                {
                    "step_number": 1,
                    "prompt_hint": "ls",
                    "expected_type": "ls",
                    "instruction": "List visible files and folders in your current directory.",
                    "what_happened": (
                        "The shell executed [bold cyan]ls[/bold cyan], which read the directory index of your current "
                        "location and listed all visible items."
                    ),
                    "breakdown": {
                        "command": "ls",
                        "parts": [
                            ("ls", "Command (List)", "Reads and displays directory entries."),
                            ("(none)", "Flags/Arguments", "Defaults to listing visible items in the current directory."),
                        ],
                        "why": "The command opened the current directory and printed the names of entries that do not start with a dot.",
                    },
                    "examples": [
                        ("ls", "Lists visible files and folders here"),
                        ("ls ~", "Lists visible contents of your home directory"),
                    ],
                },
                {
                    "step_number": 2,
                    "prompt_hint": "ls -la",
                    "expected_type": "ls_la",
                    "instruction": "List all files including hidden ones, with full details (long listing).",
                    "what_happened": (
                        "The [bold cyan]-l[/bold cyan] flag formatted each entry with permissions, ownership, file size, "
                        "and modification timestamp, while [bold cyan]-a[/bold cyan] revealed hidden items starting with `.`."
                    ),
                    "breakdown": {
                        "command": "ls -la",
                        "parts": [
                            ("ls", "Command", "The directory listing utility."),
                            ("-l", "Flag (Long format)", "Displays permissions, owner, group, byte size, and timestamp."),
                            ("-a", "Flag (All)", "Includes hidden files whose names start with a period (.)."),
                        ],
                        "why": "Combining flags as `-la` provides complete visibility into files, permissions, and directory links.",
                    },
                    "examples": [
                        ("ls -l", "Long listing format showing file details and permissions"),
                        ("ls -a", "Shows all files including hidden dotfiles"),
                        ("ls -lh", "Long listing with human-readable file sizes (KB, MB, GB)"),
                    ],
                },
            ],
            "recap": [
                "`ls` displays the files and folders located inside a directory.",
                "Flags (starting with -) modify the behavior and output format of a command.",
                "Files starting with a period (.) are hidden by default.",
                "`-l` shows detailed metadata, and `-a` reveals hidden configuration files.",
            ],
        },
        {
            "id": 4,
            "number": 4,
            "title": "Moving Around",
            "concept": (
                "Navigating between directories is the foundation of working comfortably in the terminal.\n\n"
                "The [bold cyan]cd[/bold cyan] command stands for [bold cyan]change directory[/bold cyan]. "
                "It shifts the shell's active working directory so subsequent commands operate in that new location.\n\n"
                "Linux provides two indispensable navigation shortcuts:\n"
                "• [bold green]..[/bold green] represents the [bold]parent directory[/bold] (one level up).\n"
                "• [bold green]~[/bold green] (tilde) represents your [bold]home directory[/bold]."
            ),
            "command_intro": "Practice stepping into a directory, stepping back up with `..`, and returning home with `~`.",
            "steps": [
                {
                    "step_number": 1,
                    "prompt_hint": "cd <directory>",
                    "expected_type": "cd_directory",
                    "instruction": "Step into one of the subdirectories visible in your current location.",
                    "what_happened": "The shell changed its active working directory to [bold cyan]{cwd}[/bold cyan].",
                    "breakdown": {
                        "command": "cd <directory>",
                        "parts": [
                            ("cd", "Command (Change Directory)", "Changes the shell's current working directory."),
                            ("<directory>", "Target Argument", "The name of the destination directory to enter."),
                        ],
                        "why": "The shell resolved the target directory and updated its internal working directory state.",
                    },
                    "examples": [
                        ("cd Desktop", "Enters the Desktop folder"),
                        ("cd Documents", "Enters the Documents folder"),
                        ("cd /tmp", "Jumps directly to the temporary folder"),
                    ],
                },
                {
                    "step_number": 2,
                    "prompt_hint": "cd ..",
                    "expected_type": "cd_parent",
                    "instruction": "Move up one level into the parent directory using `..`.",
                    "what_happened": "You moved up one level to the parent directory: [bold cyan]{cwd}[/bold cyan].",
                    "breakdown": {
                        "command": "cd ..",
                        "parts": [
                            ("cd", "Command", "Change directory."),
                            ("..", "Special Directory Link", "Refers to the directory immediately above the current one."),
                        ],
                        "why": "Every directory contains a `..` entry pointing to its parent, enabling upward traversal.",
                    },
                    "examples": [
                        ("cd ..", "Steps up one directory level"),
                        ("cd ../..", "Steps up two directory levels in a single command"),
                    ],
                },
                {
                    "step_number": 3,
                    "prompt_hint": "cd ~",
                    "expected_type": "cd_home",
                    "instruction": "Return to your personal home directory using the tilde shortcut `~`.",
                    "what_happened": "You returned directly to your personal home directory: [bold cyan]{cwd}[/bold cyan].",
                    "breakdown": {
                        "command": "cd ~",
                        "parts": [
                            ("cd", "Command", "Change directory."),
                            ("~", "Home Shortcut", "The shell expands ~ to the value of $HOME (/home/username)."),
                        ],
                        "why": "The shell automatically substitutes `~` with your user's home folder path.",
                    },
                    "examples": [
                        ("cd ~", "Instantly returns to your home directory from anywhere"),
                        ("cd ~/Downloads", "Navigates directly to Downloads inside your home folder"),
                        ("cd", "Running cd with no arguments also returns to your home folder"),
                    ],
                },
            ],
            "recap": [
                "`cd` (change directory) changes the shell's active working directory.",
                "`..` always refers to the parent directory one level above you.",
                "`~` is a universal shortcut for your personal home directory.",
                "Changing directories determines where subsequent commands create or find files.",
            ],
        },
        {
            "id": 5,
            "number": 5,
            "title": "Understanding Paths",
            "concept": (
                "Every file and folder in Linux has a unique address known as a [bold cyan]path[/bold cyan].\n\n"
                "There are two fundamental kinds of paths:\n"
                "1. [bold green]Absolute Paths[/bold green]: Always start at the root directory (`/`). "
                "They describe the exact location from the top of the system and work from anywhere.\n"
                "2. [bold green]Relative Paths[/bold green]: Do [italic]not[/italic] start with `/`. "
                "They describe a destination starting from wherever your shell currently happens to be.\n\n"
                "Mastering both gives you precision and speed when navigating files."
            ),
            "command_intro": "Verify your current path, reach a directory with a relative path, then reach it with an absolute path.",
            "steps": [
                {
                    "step_number": 1,
                    "prompt_hint": "pwd",
                    "expected_type": "pwd",
                    "instruction": "Print your current absolute path before navigating.",
                    "what_happened": "Your current absolute path is [bold cyan]{cwd}[/bold cyan].",
                    "breakdown": {
                        "command": "pwd",
                        "parts": [
                            ("pwd", "Command", "Print working directory."),
                        ],
                        "why": "Confirms your current starting coordinates in the filesystem tree.",
                    },
                    "examples": [
                        ("pwd", "Outputs the exact absolute path to your active directory"),
                    ],
                },
                {
                    "step_number": 2,
                    "prompt_hint": "cd <relative path>",
                    "expected_type": "cd_relative",
                    "instruction": "Enter a subdirectory using a relative path (e.g. cd <folder>).",
                    "what_happened": "Linux resolved the relative name from your previous location to arrive at: [bold cyan]{cwd}[/bold cyan].",
                    "breakdown": {
                        "command": "cd <relative path>",
                        "parts": [
                            ("cd", "Command", "Change directory."),
                            ("<relative path>", "Relative Path", "A path starting from current location without a leading slash."),
                        ],
                        "why": "The shell prepends your current working directory to the relative name.",
                    },
                    "examples": [
                        ("cd Desktop", "Relative path to a folder directly inside current directory"),
                        ("cd ./Documents", "Explicit relative path using './' (current directory)"),
                    ],
                },
                {
                    "step_number": 3,
                    "prompt_hint": "cd <absolute path>",
                    "expected_type": "cd_absolute",
                    "instruction": "Navigate to a destination using its full absolute path starting with `/`.",
                    "what_happened": "The shell evaluated the full path directly from root (`/`) to reach: [bold cyan]{cwd}[/bold cyan].",
                    "breakdown": {
                        "command": "cd <absolute path>",
                        "parts": [
                            ("cd", "Command", "Change directory."),
                            ("<absolute path>", "Absolute Path", "Full roadmap starting from system root (/)"),
                        ],
                        "why": "Absolute paths ignore where you currently are and point directly to the target location.",
                    },
                    "examples": [
                        ("cd /", "Jumps directly to system root"),
                        ("cd /tmp", "Jumps directly to the system temporary directory"),
                        ("cd /var/log", "Jumps directly to system log directory"),
                    ],
                },
            ],
            "recap": [
                "An absolute path begins with `/` and specifies an exact location from root.",
                "A relative path begins without `/` and calculates the location from where you currently are.",
                "Both path types can refer to the exact same file or folder.",
                "Relative paths are convenient for nearby files; absolute paths are unambiguous from anywhere.",
            ],
        },
    ],
}


# ============================================================
# GUIDED COMMAND VALIDATION ENGINE
# ============================================================

def validate_guided_command(
    command_str: str,
    step: Dict[str, Any],
    context: Any,
    relative_target: Optional[Path] = None,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validate learner command BEFORE execution.

    Returns:
      (is_valid, error_message, execution_ready_command)

    If not valid, returns friendly educational guidance and NEVER executes.
    """
    cleaned = command_str.strip()
    if not cleaned:
        return (
            False,
            "Please type the command shown above, or ':back' to return to the course menu.",
            None,
        )

    if cleaned.lower() in {":back", "back"}:
        return (False, "__BACK__", None)

    expected_type = step.get("expected_type", "")
    hint = step.get("prompt_hint", "")

    # Parse command tokens safely
    try:
        parts = shlex.split(cleaned)
    except ValueError:
        return (
            False,
            f"That command had an unclosed quote or syntax issue.\nTry: [bold green]{hint}[/bold green]",
            None,
        )

    if not parts:
        return (
            False,
            f"Please enter the expected command.\nTry: [bold green]{hint}[/bold green]",
            None,
        )

    cmd_name = parts[0]

    # --- Step 1: echo "Hello Linux" ---
    if expected_type == "echo_hello":
        if cmd_name != "echo":
            return (
                False,
                f"That's not the command for this step.\nTry: [bold green]{hint}[/bold green]",
                None,
            )
        arg_text = " ".join(parts[1:]).strip()
        if arg_text in {"Hello Linux", "Hello Linux!", "hello linux"}:
            return (True, None, cleaned)
        return (
            False,
            f"You ran echo, but with different text.\nTry: [bold green]{hint}[/bold green]",
            None,
        )

    # --- Step: pwd ---
    if expected_type == "pwd":
        if cleaned == "pwd":
            return (True, None, "pwd")
        return (
            False,
            f"That's not the command for this step.\nTry: [bold green]{hint}[/bold green]",
            None,
        )

    # --- Step: ls ---
    if expected_type == "ls":
        if cleaned == "ls":
            return (True, None, "ls")
        return (
            False,
            f"That's not the command for this step.\nTry: [bold green]{hint}[/bold green]",
            None,
        )

    # --- Step: ls -la ---
    if expected_type == "ls_la":
        if cmd_name != "ls":
            return (
                False,
                f"That's not the command for this step.\nTry: [bold green]{hint}[/bold green]",
                None,
            )
        flags = "".join(p.lstrip("-") for p in parts[1:] if p.startswith("-"))
        if "l" in flags and "a" in flags:
            return (True, None, cleaned)
        return (
            False,
            f"Make sure to include both the -l (long format) and -a (all files) flags.\nTry: [bold green]{hint}[/bold green]",
            None,
        )

    # --- Step: cd <directory> ---
    if expected_type == "cd_directory":
        if cmd_name != "cd":
            return (
                False,
                f"That's not the command for this step. Use `cd` to change directories.\nTry: [bold green]{hint}[/bold green]",
                None,
            )
        if len(parts) < 2:
            return (
                False,
                f"Please specify which directory to enter.\nTry: [bold green]{hint}[/bold green]",
                None,
            )
        target_name = parts[1]
        if target_name in {".", "..", "~"}:
            return (
                False,
                f"For this step, enter one of the subdirectories in your current folder.\nTry: [bold green]{hint}[/bold green]",
                None,
            )
        target_path = (context.cwd / target_name).resolve()
        if not target_path.exists() or not target_path.is_dir():
            subdirs = [
                d.name
                for d in context.cwd.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ] if context.cwd.exists() else []
            avail = ", ".join(subdirs[:4]) if subdirs else "Desktop"
            return (
                False,
                f"Directory '{target_name}' was not found here. Available directories: {avail}\nTry: [bold green]cd {subdirs[0] if subdirs else 'Desktop'}[/bold green]",
                None,
            )
        return (True, None, cleaned)

    # --- Step: cd .. ---
    if expected_type == "cd_parent":
        if cleaned in {"cd ..", "cd ../"}:
            return (True, None, "cd ..")
        return (
            False,
            f"That's not the command for this step. Use `cd ..` to move to the parent directory.\nTry: [bold green]{hint}[/bold green]",
            None,
        )

    # --- Step: cd ~ ---
    if expected_type == "cd_home":
        if cleaned in {"cd ~", "cd ~/", "cd"}:
            return (True, None, cleaned)
        return (
            False,
            f"That's not the command for this step. Use `cd ~` to return to your home directory.\nTry: [bold green]{hint}[/bold green]",
            None,
        )

    # --- Step: cd <relative path> ---
    if expected_type == "cd_relative":
        if cmd_name != "cd":
            return (
                False,
                f"That's not the command for this step.\nTry: [bold green]{hint}[/bold green]",
                None,
            )
        if len(parts) < 2:
            return (
                False,
                f"Please specify a relative directory path.\nTry: [bold green]{hint}[/bold green]",
                None,
            )
        target = parts[1]
        if target.startswith("/") or target.startswith("~"):
            return (
                False,
                "That is an absolute path (it starts with '/' or '~').\nFor this step, enter a relative path without a leading slash.",
                None,
            )
        target_path = (context.cwd / target).resolve()
        if not target_path.exists() or not target_path.is_dir():
            return (
                False,
                f"Relative path '{target}' does not exist or is not a directory.\nCheck visible directories with ls and try again.",
                None,
            )
        return (True, None, cleaned)

    # --- Step: cd <absolute path> ---
    if expected_type == "cd_absolute":
        if cmd_name != "cd":
            return (
                False,
                f"That's not the command for this step.\nTry: [bold green]{hint}[/bold green]",
                None,
            )
        if len(parts) < 2:
            return (
                False,
                f"Please specify a full absolute path starting with '/'.\nTry: [bold green]{hint}[/bold green]",
                None,
            )
        target = parts[1]
        if not target.startswith("/"):
            return (
                False,
                "That is a relative path. For this step, type the full absolute path starting with '/'.",
                None,
            )
        target_path = Path(target).resolve()
        if not target_path.exists() or not target_path.is_dir():
            return (
                False,
                f"Absolute directory '{target}' does not exist.\nMake sure the full path starts with '/' and is spelled correctly.",
                None,
            )
        return (True, None, cleaned)

    return (True, None, cleaned)


# ============================================================
# TERMINAL-NATIVE LEARNING RENDERER
# ============================================================

class LearningRenderer:
    """Provides consistent, terminal-native visual components for LinuxLearn."""

    @staticmethod
    def render_course_header(
        course: Dict[str, Any],
        completed_lessons: set[int],
        challenge_complete: bool = False,
    ):
        """Render polished course catalog header with visual progress bar."""
        total_lessons = len(course["lessons"])
        num_done = len(completed_lessons)
        pct = int((num_done / total_lessons) * 100) if total_lessons else 0

        bar_width = 18
        filled = int((num_done / total_lessons) * bar_width) if total_lessons else 0
        bar = "█" * filled + "░" * (bar_width - filled)

        title_text = Text()
        title_text.append(f"COURSE 0{course.get('id', 1)}\n", style="bold yellow")
        title_text.append(f"{course['title']}\n", style="bold white")
        title_text.append(f"{course.get('description', '')}\n\n", style="dim")
        title_text.append(f"Progress  {bar}  {num_done}/{total_lessons} completed ({pct}%)", style="bold cyan")

        panel = Panel(
            Align.center(title_text),
            border_style="cyan",
            box=ROUNDED,
            padding=(1, 3),
        )
        console.print(panel)
        console.print()

    @staticmethod
    def render_course_menu(
        course: Dict[str, Any],
        completed_lessons: set[int],
        challenge_complete: bool = False,
    ):
        """Display clean list of lessons with status indicators."""
        table = Table(
            show_header=False,
            box=None,
            padding=(0, 2),
            pad_edge=False,
        )
        table.add_column("Key", style="bold cyan", width=5)
        table.add_column("Status", width=4)
        table.add_column("Lesson", style="white")

        for index, lesson in enumerate(course["lessons"], 1):
            if index in completed_lessons:
                status = "[bold green]✓[/bold green]"
                title_style = "bold white"
            elif (not completed_lessons and index == 1) or (completed_lessons and index == max(completed_lessons) + 1):
                status = "[bold cyan]●[/bold cyan]"
                title_style = "bold cyan"
            else:
                status = "[dim]○[/dim]"
                title_style = "dim"

            table.add_row(
                f"[{index}]",
                status,
                Text(f"Lesson {index} — {lesson['title']}", style=title_style),
            )

        challenge_num = len(course["lessons"]) + 1
        ch_status = "[bold green]✓[/bold green]" if challenge_complete else "[dim]○[/dim]"
        all_lessons_done = len(completed_lessons) >= len(course["lessons"])
        ch_style = "bold yellow" if all_lessons_done and not challenge_complete else ("bold white" if challenge_complete else "dim")

        table.add_row(
            f"[{challenge_num}]",
            ch_status,
            Text("Final Challenge", style=ch_style),
        )

        table.add_row(
            "[0]",
            " ",
            Text("Back to Main Menu", style="dim"),
        )

        console.print(table)
        console.print()

    @staticmethod
    def render_lesson_banner(
        course_num: int,
        lesson_num: int,
        total_lessons: int,
        lesson_title: str,
    ):
        """Render a clean, calm lesson header."""
        bar = "─" * 70
        console.print(f"[dim]{bar}[/dim]")
        header_text = Text()
        header_text.append(f"COURSE {course_num} · LESSON {lesson_num} OF {total_lessons}  │  ", style="bold cyan")
        header_text.append(lesson_title, style="bold white")
        console.print(header_text)
        console.print(f"[dim]{bar}[/dim]\n")

    @staticmethod
    def render_concept(concept_text: str):
        """Render conceptual lesson explanation."""
        console.print(concept_text)
        console.print()

    @staticmethod
    def render_try_it(hint: str, instruction: str = ""):
        """Render prominent 'TRY IT' panel."""
        if instruction:
            console.print(f"[dim]{instruction}[/dim]")

        content = Text()
        content.append("$ ", style="bold cyan")
        content.append(hint, style="bold green")

        panel = Panel(
            content,
            title="[bold yellow]TRY IT[/bold yellow]",
            title_align="left",
            border_style="yellow",
            box=ROUNDED,
            padding=(0, 2),
            expand=False,
        )
        console.print(panel)
        console.print()

    @staticmethod
    def render_terminal_output(output: str, cwd: Optional[str] = None):
        """Render real terminal output block."""
        display = output.strip() if output.strip() else "(Command executed with no text output)"

        panel = Panel(
            Text(display, style="white"),
            title="[bold cyan]TERMINAL OUTPUT[/bold cyan]",
            title_align="left",
            border_style="cyan",
            box=ROUNDED,
            padding=(0, 2),
            expand=False,
        )
        console.print(panel)
        console.print()

    @staticmethod
    def render_what_happened(text: str, cwd: str = ""):
        """Render pedagogical explanation of what took place."""
        formatted = text.format(cwd=cwd)
        console.print("[bold cyan]WHAT JUST HAPPENED?[/bold cyan]")
        console.print(f"{formatted}\n")

    @staticmethod
    def render_command_breakdown(breakdown: Dict[str, Any]):
        """Render structured table explaining every token of the command."""
        cmd = breakdown.get("command", "")
        parts = breakdown.get("parts", [])
        why = breakdown.get("why", "")

        console.print(f"[bold cyan]COMMAND BREAKDOWN[/bold cyan]  [green]`{cmd}`[/green]")

        table = Table(
            show_header=True,
            header_style="bold cyan",
            box=SIMPLE,
            padding=(0, 2),
            expand=False,
        )
        table.add_column("Part", style="bold green", width=18)
        table.add_column("Role", style="bold yellow", width=22)
        table.add_column("What It Does", style="white")

        for item in parts:
            if len(item) == 3:
                part, role, desc = item
                table.add_row(part, role, desc)
            elif len(item) == 2:
                part, desc = item
                table.add_row(part, "Component", desc)

        console.print(table)

        if why:
            console.print(f"[dim]{why}[/dim]")
        console.print()

    @staticmethod
    def render_practical_examples(examples: List[Tuple[str, str]]):
        """Render clean list of practical examples."""
        if not examples:
            return

        console.print("[bold cyan]PRACTICAL EXAMPLES[/bold cyan]")
        table = Table(
            show_header=False,
            box=None,
            padding=(0, 2),
            pad_edge=False,
        )
        table.add_column("Command", style="bold green", width=30)
        table.add_column("Explanation", style="dim")

        for example in examples:
            if isinstance(example, tuple):
                cmd, desc = example
            elif isinstance(example, dict):
                cmd = example.get("command", "")
                desc = example.get("desc", example.get("why", ""))
            else:
                continue
            table.add_row(f"$ {cmd}", desc)

        console.print(table)
        console.print()

    @staticmethod
    def render_what_you_learned(recap_items: List[str]):
        """Render explicit 'WHAT YOU LEARNED' recap panel at the end of each lesson."""
        recap_text = Text()
        for item in recap_items:
            recap_text.append("• ", style="bold green")
            recap_text.append(f"{item}\n", style="white")

        panel = Panel(
            recap_text,
            title="[bold green]WHAT YOU LEARNED[/bold green]",
            title_align="left",
            border_style="green",
            box=ROUNDED,
            padding=(1, 2),
            expand=False,
        )
        console.print(panel)
        console.print()

    @staticmethod
    def render_next_action_prompt(
        current_lesson: int,
        total_lessons: int,
    ) -> str:
        """Prompt learner for the next action: continue to next lesson or return to menu."""
        has_next = current_lesson < total_lessons
        next_label = f"Lesson {current_lesson + 1}" if has_next else "Final Challenge"

        console.print(f"[bold cyan]Ready for {next_label}?[/bold cyan]\n")
        console.print(f"  [bold green][1][/bold green] Continue to {next_label}  [dim](or press Enter)[/dim]")
        console.print("  [bold yellow][2][/bold yellow] Back to Course Menu\n")

        try:
            choice = input("Select an option: ").strip().lower()
            return choice
        except (KeyboardInterrupt, EOFError):
            return "2"
