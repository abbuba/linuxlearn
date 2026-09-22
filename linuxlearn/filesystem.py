from __future__ import annotations

import os
import platform
import stat
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


@dataclass
class FilesystemEntry:
    """
    A safe, structured description of one filesystem object.

    This object is used as grounding information for LinuxLearn.
    It describes what exists without executing or modifying anything.
    """

    path: str
    name: str
    kind: str
    exists: bool
    is_file: bool
    is_directory: bool
    is_symlink: bool
    size_bytes: Optional[int]
    mode: Optional[str]
    modified_at: Optional[str]
    accessed_at: Optional[str]
    created_at: Optional[str]
    parent: Optional[str]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GroundingResult:
    """
    Result of grounding a path/reference against the real filesystem.
    """

    requested: str
    resolved_path: Optional[str]
    exists: bool
    kind: str
    confidence: str
    reason: str
    entry: Optional[FilesystemEntry] = None

    def to_dict(self) -> dict:
        data = asdict(self)
        if self.entry is not None:
            data["entry"] = self.entry.to_dict()
        return data


class FilesystemGrounder:
    """
    Filesystem grounding engine for LinuxLearn.

    Its responsibility is to answer:

        "What does the filesystem actually look like right now?"

    It does NOT:
        - execute shell commands
        - delete files
        - create files
        - modify files
        - decide whether an operation is safe

    Those responsibilities belong to:
        - execution layer
        - SecurityValidator
        - human approval flow

    The grounder only observes and resolves filesystem state.
    """

    DEFAULT_SEARCH_ROOTS = (
        "cwd",
        "home",
        "desktop",
        "documents",
        "downloads",
    )

    def __init__(self, context=None):
        """
        Args:
            context:
                Existing LinuxLearn TerminalContext instance.

        The dependency is intentionally optional so this class can also
        be used independently during testing.
        """

        self.context = context

    # ------------------------------------------------------------------
    # Basic path handling
    # ------------------------------------------------------------------

    @property
    def cwd(self) -> Path:
        """
        Return the current LinuxLearn working directory.

        TerminalContext is treated as the source of truth when available.
        """

        if self.context is not None:
            context_cwd = getattr(self.context, "cwd", None)

            if context_cwd:
                try:
                    return Path(context_cwd).expanduser().resolve()
                except (OSError, RuntimeError):
                    pass

        return Path.cwd().resolve()

    @property
    def home(self) -> Path:
        """
        Return the user's home directory.
        """

        if self.context is not None:
            context_home = getattr(self.context, "home", None)

            if context_home:
                try:
                    return Path(context_home).expanduser().resolve()
                except (OSError, RuntimeError):
                    pass

        return Path.home().resolve()

    def resolve_path(self, value: str | Path) -> Path:
        """
        Convert a user-facing path into an absolute normalized Path.

        Supports:

            ~/Desktop
            $HOME/Desktop
            .
            ..
            relative/path
            /absolute/path

        We do not require the target to exist.
        """

        raw = str(value).strip()

        if not raw:
            return self.cwd

        expanded = os.path.expandvars(raw)
        expanded = os.path.expanduser(expanded)

        path = Path(expanded)

        if not path.is_absolute():
            path = self.cwd / path

        try:
            return path.resolve(strict=False)
        except (OSError, RuntimeError):
            return Path(os.path.abspath(os.path.normpath(str(path))))

    def display_path(self, path: Path) -> str:
        """
        Convert an absolute path into a beginner-friendly display path.

        Example:

            /home/abbu/Desktop/project

        becomes:

            ~/Desktop/project
        """

        try:
            path = path.resolve(strict=False)

            try:
                relative = path.relative_to(self.home)
                if str(relative) == ".":
                    return "~"
                return "~/" + str(relative)
            except ValueError:
                return str(path)

        except (OSError, RuntimeError):
            return str(path)

    # ------------------------------------------------------------------
    # Filesystem inspection
    # ------------------------------------------------------------------

    def inspect(self, value: str | Path) -> FilesystemEntry:
        """
        Inspect one filesystem path without modifying it.
        """

        path = self.resolve_path(value)

        try:
            exists = path.exists()
        except OSError:
            exists = False

        if not exists:
            return FilesystemEntry(
                path=str(path),
                name=path.name or str(path),
                kind="missing",
                exists=False,
                is_file=False,
                is_directory=False,
                is_symlink=False,
                size_bytes=None,
                mode=None,
                modified_at=None,
                accessed_at=None,
                created_at=None,
                parent=str(path.parent),
            )

        try:
            is_symlink = path.is_symlink()
        except OSError:
            is_symlink = False

        try:
            is_file = path.is_file()
        except OSError:
            is_file = False

        try:
            is_directory = path.is_dir()
        except OSError:
            is_directory = False

        if is_directory:
            kind = "directory"
        elif is_file:
            kind = "file"
        elif is_symlink:
            kind = "symlink"
        else:
            kind = "other"

        size_bytes: Optional[int] = None
        mode: Optional[str] = None
        modified_at: Optional[str] = None
        accessed_at: Optional[str] = None
        created_at: Optional[str] = None

        try:
            metadata = path.stat()

            if is_file:
                size_bytes = metadata.st_size

            mode = stat.filemode(metadata.st_mode)

            modified_at = self._format_timestamp(metadata.st_mtime)
            accessed_at = self._format_timestamp(metadata.st_atime)

            if hasattr(metadata, "st_birthtime"):
                created_at = self._format_timestamp(metadata.st_birthtime)

        except (OSError, PermissionError):
            pass

        return FilesystemEntry(
            path=str(path),
            name=path.name or str(path),
            kind=kind,
            exists=True,
            is_file=is_file,
            is_directory=is_directory,
            is_symlink=is_symlink,
            size_bytes=size_bytes,
            mode=mode,
            modified_at=modified_at,
            accessed_at=accessed_at,
            created_at=created_at,
            parent=str(path.parent),
        )

    @staticmethod
    def _format_timestamp(timestamp: float) -> str:
        """
        Convert a Unix timestamp to UTC ISO-8601 format.
        """

        return datetime.fromtimestamp(
            timestamp,
            tz=timezone.utc,
        ).isoformat()

    # ------------------------------------------------------------------
    # Convenience checks
    # ------------------------------------------------------------------

    def exists(self, value: str | Path) -> bool:
        """
        Return True when the path currently exists.
        """

        return self.inspect(value).exists

    def is_directory(self, value: str | Path) -> bool:
        """
        Return True when the path currently exists and is a directory.
        """

        entry = self.inspect(value)
        return entry.exists and entry.is_directory

    def is_file(self, value: str | Path) -> bool:
        """
        Return True when the path currently exists and is a file.
        """

        entry = self.inspect(value)
        return entry.exists and entry.is_file

    # ------------------------------------------------------------------
    # Directory snapshots
    # ------------------------------------------------------------------

    def snapshot(
        self,
        directory: str | Path | None = None,
        max_entries: int = 100,
    ) -> list[dict]:
        """
        Return a bounded snapshot of a directory.

        This is intentionally limited so we do not accidentally send
        thousands of filesystem entries to the LLM.
        """

        target = self.resolve_path(directory) if directory else self.cwd

        if not target.exists():
            return []

        if not target.is_dir():
            return []

        entries: list[dict] = []

        try:
            children = sorted(
                target.iterdir(),
                key=lambda item: (
                    not item.is_dir(),
                    item.name.lower(),
                ),
            )
        except (OSError, PermissionError):
            return []

        for child in children[:max_entries]:
            try:
                info = self.inspect(child)
                entries.append(
                    {
                        "name": info.name,
                        "path": self.display_path(Path(info.path)),
                        "kind": info.kind,
                        "exists": info.exists,
                        "size_bytes": info.size_bytes,
                    }
                )
            except (OSError, RuntimeError):
                continue

        return entries

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_name(
        self,
        name: str,
        roots: Optional[Iterable[str | Path]] = None,
        max_results: int = 20,
        max_depth: int = 3,
    ) -> list[FilesystemEntry]:
        """
        Search for a filesystem object by name.

        This search is deliberately bounded.

        It is NOT intended to recursively scan the entire computer.

        Example:

            search_name("project")

        may return:

            ~/project
            ~/Desktop/project
            ~/Documents/project
        """

        clean_name = str(name).strip()

        if not clean_name:
            return []

        if roots is None:
            roots = self._default_search_roots()

        normalized_roots: list[Path] = []

        for root in roots:
            try:
                resolved = self.resolve_path(root)

                if resolved.exists() and resolved.is_dir():
                    normalized_roots.append(resolved)

            except (OSError, RuntimeError):
                continue

        results: list[FilesystemEntry] = []
        seen: set[str] = set()

        for root in normalized_roots:
            self._search_recursive(
                root=root,
                target_name=clean_name,
                max_results=max_results,
                max_depth=max_depth,
                current_depth=0,
                results=results,
                seen=seen,
            )

            if len(results) >= max_results:
                break

        return results[:max_results]

    def _search_recursive(
        self,
        root: Path,
        target_name: str,
        max_results: int,
        max_depth: int,
        current_depth: int,
        results: list[FilesystemEntry],
        seen: set[str],
    ) -> None:
        """
        Internal bounded recursive filesystem search.
        """

        if len(results) >= max_results:
            return

        if current_depth > max_depth:
            return

        try:
            children = list(root.iterdir())
        except (OSError, PermissionError):
            return

        for child in children:
            if len(results) >= max_results:
                return

            try:
                resolved_child = child.resolve(strict=False)
            except (OSError, RuntimeError):
                continue

            child_key = str(resolved_child)

            if child_key in seen:
                continue

            seen.add(child_key)

            if child.name.lower() == target_name.lower():
                try:
                    results.append(self.inspect(child))
                except (OSError, RuntimeError):
                    pass

            try:
                if child.is_dir() and not child.is_symlink():
                    self._search_recursive(
                        root=child,
                        target_name=target_name,
                        max_results=max_results,
                        max_depth=max_depth,
                        current_depth=current_depth + 1,
                        results=results,
                        seen=seen,
                    )
            except OSError:
                continue

    # ------------------------------------------------------------------
    # Default search locations
    # ------------------------------------------------------------------

    def _default_search_roots(self) -> list[Path]:
        """
        Build practical search roots for conversational resolution.
        """

        roots: list[Path] = [self.cwd, self.home]

        standard_locations = {
            "desktop": self.home / "Desktop",
            "documents": self.home / "Documents",
            "downloads": self.home / "Downloads",
            "pictures": self.home / "Pictures",
            "music": self.home / "Music",
            "videos": self.home / "Videos",
        }

        for location in standard_locations.values():
            if location.exists() and location.is_dir():
                roots.append(location)

        unique: list[Path] = []
        seen: set[str] = set()

        for root in roots:
            key = str(root.resolve(strict=False))

            if key not in seen:
                seen.add(key)
                unique.append(root)

        return unique

    # ------------------------------------------------------------------
    # Grounding
    # ------------------------------------------------------------------

    def ground(
        self,
        value: str | Path,
        search_if_missing: bool = True,
        expected_kind: Optional[str] = None,
    ) -> GroundingResult:
        """
        Ground a user/reference path against actual filesystem state.

        Resolution order:

            1. Resolve it directly.
            2. Check whether it exists.
            3. If missing and enabled, search by name.
            4. Decide whether the result is confident or ambiguous.

        This method does not modify the filesystem.
        """

        requested = str(value).strip()

        if not requested:
            return GroundingResult(
                requested=requested,
                resolved_path=None,
                exists=False,
                kind="missing",
                confidence="none",
                reason="No filesystem path or object name was provided.",
            )

        direct_path = self.resolve_path(requested)
        direct_entry = self.inspect(direct_path)

        if direct_entry.exists:
            if expected_kind:
                if self._kind_matches(
                    actual=direct_entry.kind,
                    expected=expected_kind,
                ):
                    return GroundingResult(
                        requested=requested,
                        resolved_path=str(direct_path),
                        exists=True,
                        kind=direct_entry.kind,
                        confidence="high",
                        reason="The requested path exists and matches the expected type.",
                        entry=direct_entry,
                    )

                return GroundingResult(
                    requested=requested,
                    resolved_path=str(direct_path),
                    exists=True,
                    kind=direct_entry.kind,
                    confidence="medium",
                    reason=(
                        f"The path exists, but its type is "
                        f"'{direct_entry.kind}' instead of "
                        f"'{expected_kind}'."
                    ),
                    entry=direct_entry,
                )

            return GroundingResult(
                requested=requested,
                resolved_path=str(direct_path),
                exists=True,
                kind=direct_entry.kind,
                confidence="high",
                reason="The requested path exists on the filesystem.",
                entry=direct_entry,
            )

        if not search_if_missing:
            return GroundingResult(
                requested=requested,
                resolved_path=str(direct_path),
                exists=False,
                kind="missing",
                confidence="high",
                reason="The requested path does not currently exist.",
            )

        possible_name = Path(requested).name

        if not possible_name:
            return GroundingResult(
                requested=requested,
                resolved_path=str(direct_path),
                exists=False,
                kind="missing",
                confidence="high",
                reason="The requested path does not currently exist.",
            )

        matches = self.search_name(
            possible_name,
            max_results=10,
        )

        if not matches:
            return GroundingResult(
                requested=requested,
                resolved_path=str(direct_path),
                exists=False,
                kind="missing",
                confidence="high",
                reason=(
                    "The direct path does not exist, and no matching "
                    "filesystem object was found in the bounded search roots."
                ),
            )

        if len(matches) == 1:
            match = matches[0]

            if expected_kind and not self._kind_matches(
                actual=match.kind,
                expected=expected_kind,
            ):
                return GroundingResult(
                    requested=requested,
                    resolved_path=match.path,
                    exists=True,
                    kind=match.kind,
                    confidence="medium",
                    reason=(
                        "One matching object was found, but its type does "
                        "not match the expected type."
                    ),
                    entry=match,
                )

            return GroundingResult(
                requested=requested,
                resolved_path=match.path,
                exists=True,
                kind=match.kind,
                confidence="high",
                reason=(
                    "The direct path was missing, but exactly one matching "
                    "filesystem object was found."
                ),
                entry=match,
            )

        candidate_paths = [
            self.display_path(Path(match.path))
            for match in matches
        ]

        return GroundingResult(
            requested=requested,
            resolved_path=None,
            exists=False,
            kind="ambiguous",
            confidence="low",
            reason=(
                "Multiple matching filesystem objects were found: "
                + ", ".join(candidate_paths)
            ),
        )

    @staticmethod
    def _kind_matches(actual: str, expected: str) -> bool:
        """
        Compare filesystem kinds using simple semantic aliases.
        """

        actual = actual.lower().strip()
        expected = expected.lower().strip()

        aliases = {
            "folder": "directory",
            "dir": "directory",
            "directory": "directory",
            "file": "file",
            "symlink": "symlink",
            "link": "symlink",
        }

        return aliases.get(actual, actual) == aliases.get(
            expected,
            expected,
        )

    # ------------------------------------------------------------------
    # Validate an operation target
    # ------------------------------------------------------------------

    def validate_target(
        self,
        path: str | Path,
        operation: str,
        expected_kind: Optional[str] = None,
    ) -> dict:
        """
        Check whether a target makes sense for a requested operation.

        This is a grounding check, not a security check.

        Examples:

            validate_target(
                "~/Desktop/project",
                "delete",
                expected_kind="directory"
            )

            validate_target(
                "~/Desktop/project/app.py",
                "open",
                expected_kind="file"
            )
        """

        entry = self.inspect(path)
        operation = operation.lower().strip()

        result = {
            "operation": operation,
            "requested_path": str(path),
            "resolved_path": entry.path,
            "exists": entry.exists,
            "kind": entry.kind,
            "grounded": False,
            "reason": "",
        }

        if operation in {
            "create",
            "mkdir",
            "make",
            "touch",
        }:
            if entry.exists:
                result["grounded"] = False
                result["reason"] = (
                    "The target already exists."
                )
                return result

            if not entry.parent:
                result["grounded"] = False
                result["reason"] = (
                    "The target has no valid parent directory."
                )
                return result

            parent = self.inspect(entry.parent)

            if not parent.exists:
                result["grounded"] = False
                result["reason"] = (
                    "The parent directory does not exist."
                )
                return result

            if not parent.is_directory:
                result["grounded"] = False
                result["reason"] = (
                    "The parent path exists but is not a directory."
                )
                return result

            result["grounded"] = True
            result["reason"] = (
                "The target does not exist and its parent directory exists."
            )
            return result

        if operation in {
            "delete",
            "remove",
            "rm",
            "rmdir",
            "open",
            "read",
            "copy",
            "move",
            "rename",
            "cd",
            "enter",
            "go",
        }:
            if not entry.exists:
                result["grounded"] = False
                result["reason"] = (
                    "The requested target does not exist on the filesystem."
                )
                return result

            if expected_kind and not self._kind_matches(
                actual=entry.kind,
                expected=expected_kind,
            ):
                result["grounded"] = False
                result["reason"] = (
                    f"Expected {expected_kind}, but the target is "
                    f"{entry.kind}."
                )
                return result

            result["grounded"] = True
            result["reason"] = (
                "The requested target exists and can be grounded."
            )
            return result

        result["grounded"] = entry.exists
        result["reason"] = (
            "The target was inspected. No operation-specific rule "
            "was applied."
        )

        return result

    # ------------------------------------------------------------------
    # Context integration helpers
    # ------------------------------------------------------------------

    def ground_context_path(
        self,
        attribute_name: str,
        expected_kind: Optional[str] = None,
    ) -> Optional[GroundingResult]:
        """
        Ground one of the important paths stored by TerminalContext.

        Example attributes:

            last_created_path
            last_modified_path
            last_deleted_path
            last_target_path
            cwd
        """

        if self.context is None:
            return None

        value = getattr(self.context, attribute_name, None)

        if not value:
            return None

        return self.ground(
            value,
            search_if_missing=False,
            expected_kind=expected_kind,
        )

    def ground_last_created(self) -> Optional[GroundingResult]:
        """
        Ground the most recently created path.
        """

        return self.ground_context_path(
            "last_created_path",
        )

    def ground_last_target(self) -> Optional[GroundingResult]:
        """
        Ground the most recently targeted path.
        """

        return self.ground_context_path(
            "last_target_path",
        )

    # ------------------------------------------------------------------
    # Batch grounding
    # ------------------------------------------------------------------

    def ground_many(
        self,
        paths: Iterable[str | Path],
    ) -> list[GroundingResult]:
        """
        Ground multiple paths in one operation.
        """

        results: list[GroundingResult] = []

        for path in paths:
            try:
                results.append(self.ground(path))
            except (OSError, RuntimeError, ValueError) as exc:
                results.append(
                    GroundingResult(
                        requested=str(path),
                        resolved_path=None,
                        exists=False,
                        kind="error",
                        confidence="none",
                        reason=f"Filesystem inspection failed: {exc}",
                    )
                )

        return results

    # ------------------------------------------------------------------
    # LLM-friendly representation
    # ------------------------------------------------------------------

    def get_llm_filesystem_context(
        self,
        target_paths: Optional[Iterable[str | Path]] = None,
        max_snapshot_entries: int = 60,
    ) -> dict:
        """
        Produce a bounded filesystem context packet for the LLM.

        Important:
            This method intentionally does not expose the whole machine.

        The model receives only information relevant to the current
        terminal session.
        """

        packet = {
            "current_working_directory": self.display_path(self.cwd),
            "home_directory": self.display_path(self.home),
            "platform": platform.system(),
            "architecture": platform.machine(),
            "current_directory_snapshot": self.snapshot(
                self.cwd,
                max_entries=max_snapshot_entries,
            ),
            "target_paths": [],
            "last_created_grounding": None,
            "last_target_grounding": None,
        }

        if target_paths:
            packet["target_paths"] = [
                result.to_dict()
                for result in self.ground_many(target_paths)
            ]

        last_created = self.ground_last_created()

        if last_created:
            packet["last_created_grounding"] = last_created.to_dict()

        last_target = self.ground_last_target()

        if last_target:
            packet["last_target_grounding"] = last_target.to_dict()

        return packet

    # ------------------------------------------------------------------
    # Human-readable description
    # ------------------------------------------------------------------

    def describe(
        self,
        value: str | Path,
    ) -> str:
        """
        Create a simple human-readable filesystem description.

        Useful for terminal debugging and educational messages.
        """

        result = self.ground(value)

        if result.confidence == "low":
            return (
                f"'{result.requested}' is ambiguous. "
                f"{result.reason}"
            )

        if not result.exists:
            return (
                f"'{result.requested}' does not currently exist."
            )

        path = self.display_path(
            Path(result.resolved_path)
        )

        if result.kind == "directory":
            return f"{path} exists and is a directory."

        if result.kind == "file":
            return f"{path} exists and is a file."

        if result.kind == "symlink":
            return f"{path} exists and is a symbolic link."

        return (
            f"{path} exists and is a {result.kind} filesystem object."
        )

    # ------------------------------------------------------------------
    # Debug information
    # ------------------------------------------------------------------

    def debug_report(self) -> dict:
        """
        Return a complete bounded diagnostic report.

        This is useful during development.
        """

        return {
            "cwd": self.display_path(self.cwd),
            "home": self.display_path(self.home),
            "cwd_exists": self.cwd.exists(),
            "cwd_is_directory": self.cwd.is_dir(),
            "cwd_snapshot": self.snapshot(
                self.cwd,
                max_entries=60,
            ),
            "last_created": (
                self.ground_last_created().to_dict()
                if self.ground_last_created()
                else None
            ),
            "last_target": (
                self.ground_last_target().to_dict()
                if self.ground_last_target()
                else None
            ),
        }