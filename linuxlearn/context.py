from __future__ import annotations

import json
import os
import platform
import re
import shlex
import subprocess
import time
import uuid

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional
from .filesystem import FilesystemGrounder


MAX_RECENT_COMMANDS = 20
MAX_KNOWN_ENTITIES = 500
MAX_OUTPUT_CHARS = 1600
MAX_DIRECTORY_ENTRIES = 60


@dataclass
class EntityRecord:
    path: str
    name: str
    kind: str
    exists: bool = True
    created_at: Optional[float] = None
    last_seen: Optional[float] = None
    source_command: str = ""
    aliases: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CommandRecord:
    command_id: str
    timestamp: float
    user_request: str
    command: str
    cwd_before: str
    cwd_after: str
    success: bool
    exit_code: Optional[int]
    duration_ms: int
    stdout: str = ""
    stderr: str = ""
    created_paths: list[str] = field(default_factory=list)
    modified_paths: list[str] = field(default_factory=list)
    deleted_paths: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class TerminalContext:
    """
    Persistent world-state engine for one LinuxLearn session.

    The LLM does NOT own this state.
    LinuxLearn owns this state and supplies a controlled context packet
    to the LLM for every request.
    """

    def __init__(self, initial_cwd: Optional[str | Path] = None):
        self.session_id = str(uuid.uuid4())
        self.started_at = time.time()

        self.home = Path.home().resolve()

        starting_cwd = (
            Path(initial_cwd).expanduser()
            if initial_cwd
            else Path.cwd()
        )

        self.cwd = starting_cwd.resolve()
        self.previous_cwd: Optional[Path] = None

        self.last_command = ""
        self.last_successful_command = ""
        self.last_failed_command = ""

        self.last_created_path: Optional[Path] = None
        self.last_modified_path: Optional[Path] = None
        self.last_deleted_path: Optional[Path] = None
        self.last_target_path: Optional[Path] = None

        self.last_exit_code: Optional[int] = None
        self.last_command_success = False

        self.command_history: list[CommandRecord] = []

        # Canonical path -> entity metadata.
        self.known_entities: dict[str, EntityRecord] = {}

        # Small set of shell variables changed explicitly through LinuxLearn.
        self.shell_overrides: dict[str, str] = {}

        self.shell_aliases: dict[str, str] = {}

        self.standard_locations = {
            "desktop": self.home / "Desktop",
            "documents": self.home / "Documents",
            "downloads": self.home / "Downloads",
            "pictures": self.home / "Pictures",
            "music": self.home / "Music",
            "videos": self.home / "Videos",
            "home": self.home,
        }

        self.filesystem = FilesystemGrounder(self)

        self._runtime_cache: dict[str, Any] = {}
        self._runtime_cache_time = 0.0

        self.register_path(self.cwd, source_command="session_start")

        for path in self.standard_locations.values():
            if path.exists():
                self.register_path(
                    path,
                    source_command="standard_location_detection",
                )

    # =========================================================
    # BASIC PATH HANDLING
    # =========================================================

    def _expand_environment(self, value: str) -> str:
        expanded = value

        expanded = expanded.replace(
            "${HOME}",
            str(self.home),
        )

        expanded = expanded.replace(
            "$HOME",
            str(self.home),
        )

        expanded = expanded.replace(
            "${PWD}",
            str(self.cwd),
        )

        expanded = expanded.replace(
            "$PWD",
            str(self.cwd),
        )

        for key, val in self.shell_overrides.items():
            expanded = expanded.replace(
                f"${key}",
                val,
            )
            expanded = expanded.replace(
                f"${{{key}}}",
                val,
            )

        return os.path.expandvars(expanded)

    def resolve_path(
        self,
        raw_path: str,
        base: Optional[Path] = None,
    ) -> Path:
        """
        Resolve:
        - ~
        - $HOME
        - $PWD
        - standard locations such as desktop
        - relative paths
        - absolute paths
        - ..
        """

        value = raw_path.strip().strip("\"'")

        if not value:
            return self.cwd.resolve()

        normalized = value.lower().strip()

        if normalized in self.standard_locations:
            return self.standard_locations[
                normalized
            ].resolve()

        value = self._expand_environment(value)
        value = os.path.expanduser(value)

        path = Path(value)

        if path.is_absolute():
            return path.resolve()

        anchor = base or self.cwd

        return (
            anchor / path
        ).resolve()

    def get_display_cwd(self) -> str:
        """
        Return paths in user-friendly form.

        Example:
            /home/user/Desktop/linuxlearn
        becomes:
            ~/Desktop/linuxlearn
        """

        try:
            relative = self.cwd.relative_to(
                self.home
            )

            if str(relative) == ".":
                return "~/"

            return "~/" + str(relative)

        except ValueError:
            return str(self.cwd)

    # =========================================================
    # DIRECTORY STATE
    # =========================================================

    def update_cwd(
        self,
        target_path: str,
    ) -> bool:
        """
        Persistently update LinuxLearn's current directory.

        This is the fix for the original:
            cd desktop
            cd ab
        problem.

        A temporary subprocess cannot remember cd.
        TerminalContext can.
        """

        target = target_path.strip()

        if target == "-":
            if self.previous_cwd and self.previous_cwd.is_dir():
                old = self.cwd
                self.cwd = self.previous_cwd
                self.previous_cwd = old
                self.register_path(
                    self.cwd,
                    source_command="cd -",
                )
                return True

            return False

        resolved = self.resolve_path(target)

        if not resolved.is_dir():
            return False

        old = self.cwd

        self.previous_cwd = old
        self.cwd = resolved

        self.register_path(
            self.cwd,
            source_command="directory_navigation",
        )

        return True

    # =========================================================
    # ENTITY REGISTRY
    # =========================================================

    def register_path(
        self,
        path: str | Path,
        source_command: str = "",
        alias: Optional[str] = None,
    ) -> Optional[EntityRecord]:
        """
        Add a file/folder to LinuxLearn's known world model.
        """

        try:
            resolved = Path(path).expanduser().resolve()
        except Exception:
            return None

        try:
            exists = resolved.exists()

            if resolved.is_dir():
                kind = "directory"
            elif resolved.is_file():
                kind = "file"
            elif resolved.is_symlink():
                kind = "symlink"
            else:
                kind = "unknown"

            name = resolved.name or str(resolved)

            key = str(resolved)

            now = time.time()

            existing = self.known_entities.get(key)

            if existing:
                existing.exists = exists
                existing.last_seen = now

                if source_command:
                    existing.source_command = source_command

                if alias and alias not in existing.aliases:
                    existing.aliases.append(alias)

                return existing

            entity = EntityRecord(
                path=key,
                name=name,
                kind=kind,
                exists=exists,
                created_at=now,
                last_seen=now,
                source_command=source_command,
                aliases=(
                    [alias]
                    if alias
                    else []
                ),
            )

            self.known_entities[key] = entity

            self._trim_entities()

            return entity

        except Exception:
            return None

    def _trim_entities(self):
        if len(self.known_entities) <= MAX_KNOWN_ENTITIES:
            return

        entities = sorted(
            self.known_entities.items(),
            key=lambda item: (
                item[1].last_seen or 0
            ),
            reverse=True,
        )

        self.known_entities = dict(
            entities[:MAX_KNOWN_ENTITIES]
        )

    def mark_deleted(
        self,
        path: str | Path,
        source_command: str = "",
    ):
        resolved = self.resolve_path(str(path))
        key = str(resolved)

        entity = self.known_entities.get(key)

        if entity:
            entity.exists = False
            entity.last_seen = time.time()
            entity.source_command = source_command
        else:
            self.known_entities[key] = EntityRecord(
                path=key,
                name=resolved.name,
                kind="unknown",
                exists=False,
                last_seen=time.time(),
                source_command=source_command,
            )

        self.last_deleted_path = resolved

    def find_entity(
        self,
        name: str,
    ) -> Optional[EntityRecord]:
        target = name.strip().strip("\"'").lower()

        if not target:
            return None

        # Exact known path/name match.
        for entity in self.known_entities.values():
            if not entity.exists:
                continue

            if entity.name.lower() == target:
                return entity

            if target in {
                alias.lower()
                for alias in entity.aliases
            }:
                return entity

        # Standard locations.
        if target in self.standard_locations:
            path = self.standard_locations[target]

            if path.exists():
                return self.register_path(path)

        # Search immediate children of current directory.
        for child in self.cwd.iterdir():
            if child.name.lower() == target:
                return self.register_path(child)

        return None

    def find_named_path(
        self,
        name: str,
    ) -> Optional[Path]:
        """
        Conservative filesystem grounding.

        Search only likely user locations rather than scanning the
        entire machine.
        """

        normalized = name.strip().strip("\"'").lower()

        if not normalized:
            return None

        entity = self.find_entity(normalized)

        if entity:
            return Path(entity.path)

        roots = [
            self.cwd,
            self.home / "Desktop",
            self.home / "Documents",
            self.home / "Downloads",
        ]

        seen = set()

        for root in roots:
            try:
                root = root.resolve()
            except Exception:
                continue

            if str(root) in seen or not root.is_dir():
                continue

            seen.add(str(root))

            try:
                for child in root.iterdir():
                    if (
                        child.name.lower()
                        == normalized
                    ):
                        self.register_path(
                            child,
                            source_command="filesystem_grounding",
                        )
                        return child.resolve()

            except Exception:
                continue

        return None

    # =========================================================
    # REFERENCE RESOLUTION
    # =========================================================

    def resolve_references(
        self,
        user_request: str,
    ) -> dict:
        """
        Resolve human references such as:

            that
            it
            this folder
            there
            the folder named ab
            the file we just created
        """

        text = user_request.strip()
        lower = text.lower()

        result = {
            "resolved": [],
            "unresolved": [],
        }

        last_relevant = (
            self.last_created_path
            or self.last_target_path
            or self.last_modified_path
        )

        # -----------------------------------------------------
        # THAT / IT / THIS / THERE
        # -----------------------------------------------------

        pronoun_patterns = [
            "that",
            "that folder",
            "that directory",
            "that file",
            "it",
            "this folder",
            "this directory",
            "this file",
            "there",
            "the folder we just created",
            "the directory we just created",
            "the file we just created",
            "the thing we just created",
        ]

        for phrase in pronoun_patterns:
            if phrase in lower:
                if last_relevant:
                    result["resolved"].append(
                        {
                            "reference": phrase,
                            "path": str(last_relevant),
                            "reason": "recent_terminal_state",
                        }
                    )
                else:
                    result["unresolved"].append(
                        phrase
                    )

        # -----------------------------------------------------
        # "FOLDER NAMED X"
        # -----------------------------------------------------

        patterns = [
            r"(?:folder|directory|file)"
            r"\s+(?:named|called)\s+"
            r"([a-zA-Z0-9._-]+)",

            r"(?:folder|directory|file)"
            r"\s+([a-zA-Z0-9._-]+)",
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                lower,
            )

            if not match:
                continue

            name = match.group(1)

            entity = self.find_entity(name)

            if entity:
                result["resolved"].append(
                    {
                        "reference": name,
                        "path": entity.path,
                        "kind": entity.kind,
                        "reason": "known_entity",
                    }
                )
            else:
                found = self.find_named_path(name)

                if found:
                    result["resolved"].append(
                        {
                            "reference": name,
                            "path": str(found),
                            "reason": "filesystem_grounding",
                        }
                    )
                else:
                    result["unresolved"].append(
                        name
                    )

        # -----------------------------------------------------
        # STANDARD LOCATIONS
        # -----------------------------------------------------

        for location_name, path in self.standard_locations.items():
            if re.search(
                rf"\b{re.escape(location_name)}\b",
                lower,
            ):
                result["resolved"].append(
                    {
                        "reference": location_name,
                        "path": str(path),
                        "reason": "standard_location",
                        "exists": path.exists(),
                    }
                )

        # Remove duplicates.
        unique = []
        seen = set()

        for item in result["resolved"]:
            key = (
                item["reference"],
                item["path"],
            )

            if key in seen:
                continue

            seen.add(key)
            unique.append(item)

        result["resolved"] = unique

        return result

    # =========================================================
    # SHELL-STATE COMMANDS
    # =========================================================

    def parse_simple_cd(
        self,
        command: str,
    ) -> Optional[str]:
        """
        Recognizes only a simple cd command.

        Examples:
            cd desktop
            cd ..
            cd "$HOME/Desktop/ab"
            cd -

        Compound commands are deliberately not treated as internal.
        """

        try:
            parts = shlex.split(command)
        except ValueError:
            return None

        if not parts:
            return None

        if parts[0] != "cd":
            return None

        if len(parts) == 1:
            return "~"

        if len(parts) == 2:
            return parts[1]

        return None

    def parse_simple_export(
        self,
        command: str,
    ) -> Optional[tuple[str, str]]:
        match = re.fullmatch(
            r"\s*export\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)="
            r"(.*)\s*",
            command,
        )

        if not match:
            return None

        key = match.group(1)
        value = match.group(2).strip().strip("\"'")

        value = self._expand_environment(value)

        return key, value

    def parse_simple_unset(
        self,
        command: str,
    ) -> Optional[str]:
        match = re.fullmatch(
            r"\s*unset\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)\s*",
            command,
        )

        if not match:
            return None

        return match.group(1)

    def handle_internal_command(
        self,
        command: str,
    ) -> Optional[dict]:
        """
        Handle stateful commands that should not be delegated to an
        isolated Bash process.
        """

        cd_target = self.parse_simple_cd(command)

        if cd_target is not None:
            previous = self.get_display_cwd()

            success = self.update_cwd(
                cd_target
            )

            return {
                "handled": True,
                "type": "cd",
                "success": success,
                "previous_cwd": previous,
                "current_cwd": self.get_display_cwd(),
                "target": cd_target,
            }

        exported = self.parse_simple_export(command)

        if exported:
            key, value = exported

            self.shell_overrides[key] = value

            return {
                "handled": True,
                "type": "export",
                "success": True,
                "variable": key,
            }

        unset_key = self.parse_simple_unset(command)

        if unset_key:
            self.shell_overrides.pop(
                unset_key,
                None,
            )

            return {
                "handled": True,
                "type": "unset",
                "success": True,
                "variable": unset_key,
            }

        return None

    def execution_env(self) -> dict:
        env = os.environ.copy()
        env.update(self.shell_overrides)
        return env

    # =========================================================
    # COMMAND PATH INFERENCE
    # =========================================================

    def _normalize_command_path(
        self,
        raw: str,
    ) -> Optional[Path]:
        value = raw.strip().strip("\"'")

        if not value:
            return None

        # Brace expansion:
        # /foo/ab/{1..100}
        value = re.sub(
            r"/?\{[^{}]+\}",
            "",
            value,
        )

        if value.endswith("/"):
            value = value[:-1]

        if not value:
            return None

        return self.resolve_path(
            value
        )

    def infer_command_paths(
        self,
        command: str,
    ) -> dict:
        """
        Best-effort extraction of affected paths.

        This enriches context only.
        It is NOT a security mechanism.
        """

        result = {
            "created_paths": [],
            "modified_paths": [],
            "deleted_paths": [],
        }

        try:
            parts = shlex.split(command)
        except ValueError:
            return result

        if not parts:
            return result

        executable = parts[0]

        # -----------------------------------------------------
        # mkdir / touch
        # -----------------------------------------------------

        if executable in {
            "mkdir",
            "touch",
        }:
            for part in parts[1:]:
                if part.startswith("-"):
                    continue

                path = self._normalize_command_path(
                    part
                )

                if path:
                    result[
                        "created_paths"
                    ].append(str(path))

        # -----------------------------------------------------
        # rm / rmdir
        # -----------------------------------------------------

        elif executable in {
            "rm",
            "rmdir",
        }:
            for part in parts[1:]:
                if part.startswith("-"):
                    continue

                path = self._normalize_command_path(
                    part
                )

                if path:
                    result[
                        "deleted_paths"
                    ].append(str(path))

        # -----------------------------------------------------
        # cp
        # -----------------------------------------------------

        elif executable == "cp":
            candidates = [
                p
                for p in parts[1:]
                if not p.startswith("-")
            ]

            if len(candidates) >= 2:
                destination = self._normalize_command_path(
                    candidates[-1]
                )

                if destination:
                    result[
                        "created_paths"
                    ].append(str(destination))

        # -----------------------------------------------------
        # mv
        # -----------------------------------------------------

        elif executable == "mv":
            candidates = [
                p
                for p in parts[1:]
                if not p.startswith("-")
            ]

            if len(candidates) >= 2:
                source = self._normalize_command_path(
                    candidates[0]
                )
                destination = self._normalize_command_path(
                    candidates[-1]
                )

                if source:
                    result[
                        "deleted_paths"
                    ].append(str(source))

                if destination:
                    result[
                        "created_paths"
                    ].append(str(destination))

        return result

    # =========================================================
    # FILESYSTEM SNAPSHOT
    # =========================================================

    def directory_snapshot(
        self,
        directory: Optional[Path] = None,
        max_entries: int = MAX_DIRECTORY_ENTRIES,
    ) -> list[dict]:
        target = directory or self.cwd

        if not target.is_dir():
            return []

        entries = []

        try:
            children = sorted(
                target.iterdir(),
                key=lambda p: (
                    not p.is_dir(),
                    p.name.lower(),
                ),
            )

            for child in children[:max_entries]:
                try:
                    kind = (
                        "directory"
                        if child.is_dir()
                        else "file"
                        if child.is_file()
                        else "other"
                    )

                    item = {
                        "name": child.name,
                        "type": kind,
                    }

                    if kind == "file":
                        try:
                            item["size_bytes"] = child.stat().st_size
                        except Exception:
                            pass

                    entries.append(item)

                except Exception:
                    continue

        except Exception:
            return []

        return entries

    # =========================================================
    # SYSTEM / WORKSPACE CONTEXT
    # =========================================================

    def _read_os_release(self) -> dict:
        result = {}

        path = Path(
            "/etc/os-release"
        )

        if not path.exists():
            return result

        try:
            for line in path.read_text(
                encoding="utf-8",
                errors="ignore",
            ).splitlines():
                if "=" not in line:
                    continue

                key, value = line.split(
                    "=",
                    1,
                )

                result[key] = value.strip().strip("\"'")

        except Exception:
            pass

        return result

    def _get_git_context(self) -> dict:
        try:
            root_result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(self.cwd),
                    "rev-parse",
                    "--show-toplevel",
                ],
                capture_output=True,
                text=True,
                timeout=1.5,
            )

            if root_result.returncode != 0:
                return {
                    "is_git_repository": False,
                }

            root = root_result.stdout.strip()

            branch_result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(self.cwd),
                    "branch",
                    "--show-current",
                ],
                capture_output=True,
                text=True,
                timeout=1.5,
            )

            status_result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(self.cwd),
                    "status",
                    "--porcelain",
                ],
                capture_output=True,
                text=True,
                timeout=1.5,
            )

            return {
                "is_git_repository": True,
                "root": root,
                "branch": branch_result.stdout.strip(),
                "dirty": bool(
                    status_result.stdout.strip()
                ),
            }

        except Exception:
            return {
                "is_git_repository": False,
            }

    def get_workspace_context(self) -> dict:
        now = time.time()

        if (
            now - self._runtime_cache_time
            < 5
            and self._runtime_cache
        ):
            return self._runtime_cache

        os_release = self._read_os_release()

        markers = [
            "pyproject.toml",
            "package.json",
            "requirements.txt",
            "Makefile",
            "Cargo.toml",
            "go.mod",
            "README.md",
            ".git",
        ]

        present_markers = [
            marker
            for marker in markers
            if (self.cwd / marker).exists()
        ]

        workspace = {
            "current_directory": self.get_display_cwd(),
            "current_directory_absolute": str(self.cwd),
            "project_markers": present_markers,
            "git": self._get_git_context(),
            "platform": platform.system(),
            "architecture": platform.machine(),
            "python": platform.python_version(),
            "shell": os.environ.get(
                "SHELL",
                "/bin/bash",
            ),
            "distribution": os_release.get(
                "PRETTY_NAME",
                "Linux",
            ),
        }

        self._runtime_cache = workspace
        self._runtime_cache_time = now

        return workspace

    def get_safe_environment(self) -> dict:
        """
        Never dump the whole environment to the LLM.

        In particular, API keys and unrelated secrets should not become
        part of the context packet.
        """

        allowed = {
            "USER",
            "LOGNAME",
            "SHELL",
            "LANG",
            "LC_ALL",
            "TERM",
            "VIRTUAL_ENV",
            "PWD",
        }

        result = {}

        for key in allowed:
            value = os.environ.get(key)

            if value:
                result[key] = value

        result.update(
            self.shell_overrides
        )

        return result

    # =========================================================
    # COMMAND HISTORY
    # =========================================================

    def record_action(
        self,
        *,
        user_request: str,
        command: str,
        success: bool,
        exit_code: Optional[int],
        duration_ms: int,
        stdout: str = "",
        stderr: str = "",
        created_paths: Optional[list[str]] = None,
        modified_paths: Optional[list[str]] = None,
        deleted_paths: Optional[list[str]] = None,
        target_path: Optional[str] = None,
        cwd_before: Optional[str] = None,
    ):
        created_paths = created_paths or []
        modified_paths = modified_paths or []
        deleted_paths = deleted_paths or []

        before = (
            cwd_before
            or self.get_display_cwd()
        )

        # Register filesystem changes.
        for path in created_paths:
            resolved = self.resolve_path(path)

            self.register_path(
                resolved,
                source_command=command,
            )

            self.last_created_path = resolved

        for path in modified_paths:
            resolved = self.resolve_path(path)

            self.register_path(
                resolved,
                source_command=command,
            )

            self.last_modified_path = resolved

        for path in deleted_paths:
            self.mark_deleted(
                path,
                source_command=command,
            )

        if target_path:
            self.last_target_path = (
                self.resolve_path(target_path)
            )

        after = self.get_display_cwd()

        record = CommandRecord(
            command_id=str(
                uuid.uuid4()
            ),
            timestamp=time.time(),
            user_request=user_request,
            command=command,
            cwd_before=before,
            cwd_after=after,
            success=success,
            exit_code=exit_code,
            duration_ms=duration_ms,
            stdout=self._truncate_output(
                stdout
            ),
            stderr=self._truncate_output(
                stderr
            ),
            created_paths=[
                str(self.resolve_path(p))
                for p in created_paths
            ],
            modified_paths=[
                str(self.resolve_path(p))
                for p in modified_paths
            ],
            deleted_paths=[
                str(self.resolve_path(p))
                for p in deleted_paths
            ],
        )

        self.command_history.append(
            record
        )

        if len(self.command_history) > MAX_RECENT_COMMANDS:
            self.command_history = (
                self.command_history[
                    -MAX_RECENT_COMMANDS:
                ]
            )

        self.last_command = command
        self.last_exit_code = exit_code
        self.last_command_success = success

        if success:
            self.last_successful_command = command
        else:
            self.last_failed_command = command

    @staticmethod
    def _truncate_output(
        value: str,
    ) -> str:
        if not value:
            return ""

        if len(value) <= MAX_OUTPUT_CHARS:
            return value

        return (
            "... "
            + value[-MAX_OUTPUT_CHARS:]
        )

    def ground_path(
        self,
        path,
        search_if_missing=True,
        expected_kind=None,
    ):
        """
        Verify a path/reference against the real filesystem.
        TerminalContext remembers what happened.
        FilesystemGrounder verifies what exists right now.
        """
        return self.filesystem.ground(
            path,
            search_if_missing=search_if_missing,
            expected_kind=expected_kind,
        )

    def ground_last_created(self):
        """
        Verify whether the object remembered as the most recently
        created object still exists.
        """
        return self.filesystem.ground_last_created()

    def ground_last_target(self):
        """
        Verify whether the most recently targeted object still exists.
        """
        return self.filesystem.ground_last_target()

    def get_filesystem_context(
        self,
        target_paths=None,
    ):
        """
        Return bounded, LLM-safe filesystem information.
        """
        return self.filesystem.get_llm_filesystem_context(
            target_paths=target_paths,
        )

    # =========================================================
    # LLM CONTEXT PACKET
    # =========================================================

    def get_llm_context(
        self,
        user_request: str,
    ) -> str:
        """
        Build the controlled context packet sent to the model.

        This is intentionally structured rather than dumping the entire
        terminal history.
        """

        references = self.resolve_references(
            user_request
        )

        recent_history = [
            {
                "request": item.user_request,
                "command": item.command,
                "cwd_before": item.cwd_before,
                "cwd_after": item.cwd_after,
                "success": item.success,
                "exit_code": item.exit_code,
                "created_paths": item.created_paths,
                "deleted_paths": item.deleted_paths,
                "stdout": item.stdout,
                "stderr": item.stderr,
            }
            for item in self.command_history[-8:]
        ]

        known_entities = []

        for entity in self.known_entities.values():
            if not entity.exists:
                continue

            known_entities.append(
                entity.to_dict()
            )

        known_entities = sorted(
            known_entities,
            key=lambda item: item.get(
                "last_seen",
                0,
            ),
            reverse=True,
        )[:30]

        workspace = self.get_workspace_context()

        filesystem = self.get_filesystem_context()

        important_state = {
            "last_created_path":
                (
                    str(self.last_created_path)
                    if self.last_created_path
                    else None
                ),
            "last_modified_path":
                (
                    str(self.last_modified_path)
                    if self.last_modified_path
                    else None
                ),
            "last_deleted_path":
                (
                    str(self.last_deleted_path)
                    if self.last_deleted_path
                    else None
                ),
            "last_target_path":
                (
                    str(self.last_target_path)
                    if self.last_target_path
                    else None
                ),
            "last_command":
                self.last_command,
            "last_successful_command":
                self.last_successful_command,
            "last_failed_command":
                self.last_failed_command,
        }

        packet = {
            "session": {
                "session_id": self.session_id,
            },
            "terminal": workspace,
            "home": str(self.home),
            "environment": self.get_safe_environment(),
            "important_state": important_state,
            "resolved_references": references,
            "known_entities": known_entities,
            "filesystem": filesystem,
            "recent_history": recent_history,
        }

        return json.dumps(
            packet,
            indent=2,
            ensure_ascii=False,
        )

    # =========================================================
    # SESSION/PDF DATA
    # =========================================================

    def get_session_summary(self) -> dict:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "current_directory": str(
                self.cwd
            ),
            "current_directory_display":
                self.get_display_cwd(),
            "last_command": self.last_command,
            "last_successful_command":
                self.last_successful_command,
            "last_created_path": (
                str(self.last_created_path)
                if self.last_created_path
                else None
            ),
            "last_target_path": (
                str(self.last_target_path)
                if self.last_target_path
                else None
            ),
            "known_entities": [
                entity.to_dict()
                for entity
                in self.known_entities.values()
            ],
            "command_history": [
                record.to_dict()
                for record
                in self.command_history
            ],
        }