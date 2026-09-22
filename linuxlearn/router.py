import re
from pathlib import Path


class FastPathRouter:
    """
    Conservative deterministic router for common Linux commands.

    Important:
    FastPath should only return a command when it can confidently
    understand the user's request. Otherwise it returns None so the
    LLM can handle the request.
    """

    @staticmethod
    def _resolve_location(location: str, context=None) -> str:
        """
        Resolve a natural-language location using TerminalContext.
        Examples:
            desktop
            documents
            downloads
            current folder
            .
            ~
        """
        location = location.strip().lower()

        if not location:
            return "$HOME"

        if context is not None:
            try:
                return str(context.resolve_path(location))
            except Exception:
                pass

        if location in {"desktop", "the desktop"}:
            return "$HOME/Desktop"
        if location in {"documents", "the documents"}:
            return "$HOME/Documents"
        if location in {"downloads", "the downloads"}:
            return "$HOME/Downloads"
        if location in {"home", "home directory"}:
            return "$HOME"
        if location in {
            "current folder",
            "this folder",
            "current directory",
            "this directory",
            ".",
            "~",
        }:
            if context is not None:
                return str(context.cwd)
            return "."

        return location

    @staticmethod
    def _proposal(
        command,
        explanation,
        concept,
        risk="low",
        requires_sudo=False,
    ):
        return {
            "command": command,
            "explanation": explanation,
            "concept": concept,
            "risk": risk,
            "requires_sudo": requires_sudo,
            "source": "fast_path",
        }

    @staticmethod
    def _normalize(text):
        text = text.strip().lower()
        text = re.sub(r"\s+", " ", text)
        return text

    @staticmethod
    def _linux_path(path):
        """
        Convert common natural-language locations into safe shell paths.

        Examples:
            desktop -> "$HOME/Desktop"
            documents -> "$HOME/Documents"
            downloads -> "$HOME/Downloads"
            home -> "$HOME"
        """
        path = path.strip().strip("\"'")

        aliases = {
            "desktop": "$HOME/Desktop",
            "the desktop": "$HOME/Desktop",
            "documents": "$HOME/Documents",
            "document": "$HOME/Documents",
            "downloads": "$HOME/Downloads",
            "download": "$HOME/Downloads",
            "pictures": "$HOME/Pictures",
            "pictures folder": "$HOME/Pictures",
            "music": "$HOME/Music",
            "videos": "$HOME/Videos",
            "home": "$HOME",
            "home folder": "$HOME",
        }

        normalized = FastPathRouter._normalize(path)

        if normalized in aliases:
            return aliases[normalized]

        if normalized.startswith("~/"):
            return normalized

        if normalized.startswith("/"):
            return normalized

        return None

    @staticmethod
    def _clean_name(name):
        """
        Clean a user-provided filename/folder name.

        Returns None for unsafe/ambiguous values.
        """
        name = name.strip().strip("\"'")

        if not name:
            return None

        # Don't allow shell syntax to enter deterministic commands.
        if any(char in name for char in [";", "|", "&", "`", "$", ">", "<"]):
            return None

        # A name containing a path separator is better handled by the LLM.
        if "/" in name or "\\" in name:
            return None

        return name

    @classmethod
    def match(cls, user_input: str, context=None):
        text = cls._normalize(user_input)

        # ====================================================
        # CREATE FOLDER / DIRECTORY
        # ====================================================

        folder_patterns = [
            r"^make (?:a )?folder (?:on|in) (.+?) (?:called|named) (.+)$",
            r"^create (?:a )?folder (?:on|in) (.+?) (?:called|named) (.+)$",
            r"^make (?:a )?directory (?:on|in) (.+?) (?:called|named) (.+)$",
            r"^create (?:a )?directory (?:on|in) (.+?) (?:called|named) (.+)$",
            r"^make (?:a )?folder (?:called|named) (.+?) (?:on|in) (.+)$",
            r"^create (?:a )?folder (?:called|named) (.+?) (?:on|in) (.+)$",
            r"^make (?:a )?directory (?:called|named) (.+?) (?:on|in) (.+)$",
            r"^create (?:a )?directory (?:called|named) (.+?) (?:on|in) (.+)$",
        ]

        for index, pattern in enumerate(folder_patterns):
            match = re.match(pattern, text)

            if not match:
                continue

            first = match.group(1).strip()
            second = match.group(2).strip()

            if index < 4:
                location_text = first
                name_text = second
            else:
                name_text = first
                location_text = second

            location = cls._resolve_location(location_text, context)
            name = cls._clean_name(name_text)

            if location and name:
                command = f'mkdir -p "{location}/{name}"'

                return cls._proposal(
                    command=command,
                    explanation=(
                        f'Creates a new folder named "{name}" '
                        f'inside {location_text}.'
                    ),
                    concept="Directory Creation",
                    risk="low",
                    requires_sudo=False,
                )

        # ====================================================
        # SIMPLE FOLDER IN CURRENT DIRECTORY
        # ====================================================

        simple_folder_patterns = [
            r"^make (?:a )?folder (?:called|named) (.+)$",
            r"^create (?:a )?folder (?:called|named) (.+)$",
            r"^make (?:a )?directory (?:called|named) (.+)$",
            r"^create (?:a )?directory (?:called|named) (.+)$",
        ]

        for pattern in simple_folder_patterns:
            match = re.match(pattern, text)

            if not match:
                continue

            name = FastPathRouter._clean_name(match.group(1))

            if name:
                current_location = cls._resolve_location("current directory", context)
                return cls._proposal(
                    command=f'mkdir -p "{current_location}/{name}"',
                    explanation=(
                        f'Creates a new folder named "{name}" '
                        f'in the current directory.'
                    ),
                    concept="Directory Creation",
                )

        # ====================================================
        # PRESENT WORKING DIRECTORY
        # ====================================================

        if text in {
            "where am i",
            "what directory am i in",
            "what folder am i in",
            "show my current directory",
            "show current directory",
            "print working directory",
        }:
            return cls._proposal(
                command="pwd",
                explanation="Shows the full path of your current directory.",
                concept="Working Directory",
            )

        # ====================================================
        # LIST FILES
        # ====================================================

        if text in {
            "list files",
            "show files",
            "list files here",
            "show files here",
            "what files are here",
            "show me the files",
        }:
            return cls._proposal(
                command="ls -la",
                explanation="Lists files and directories in the current directory.",
                concept="Directory Listing",
            )

        # ====================================================
        # LIST DESKTOP
        # ====================================================

        if text in {
            "show desktop files",
            "list desktop files",
            "what is on my desktop",
            "show me my desktop",
            "list my desktop",
        }:
            return cls._proposal(
                command='ls -la "$HOME/Desktop"',
                explanation="Lists the files and folders currently on your Desktop.",
                concept="Directory Listing",
            )

        # ====================================================
        # CHANGE DIRECTORY
        # ====================================================

        cd_patterns = [
            r"^go to (?:the )?(.+)$",
            r"^open (?:the )?(.+)$",
            r"^change directory to (.+)$",
            r"^cd (.+)$",
        ]

        for pattern in cd_patterns:
            match = re.match(pattern, text)

            if not match:
                continue

            target_text = match.group(1).strip()
            target = cls._resolve_location(target_text, context)

            if target:
                return cls._proposal(
                    command=f'cd "{target}"',
                    explanation=f"Changes the current directory to {target_text}.",
                    concept="Directory Navigation",
                )

        # ====================================================
        # CREATE EMPTY FILE
        # ====================================================

        file_patterns = [
            r"^create (?:an )?file (?:called|named) (.+)$",
            r"^make (?:an )?file (?:called|named) (.+)$",
            r"^create (?:a )?file (?:called|named) (.+)$",
        ]

        for pattern in file_patterns:
            match = re.match(pattern, text)

            if not match:
                continue

            filename = FastPathRouter._clean_name(match.group(1))

            if filename:
                return cls._proposal(
                    command=f'touch "{filename}"',
                    explanation=f'Creates an empty file named "{filename}".',
                    concept="File Creation",
                )

        # ====================================================
        # INSTALL PACKAGE
        # ====================================================

        install_patterns = [
            r"^install ([a-z0-9._+-]+)$",
            r"^install the package ([a-z0-9._+-]+)$",
            r"^i want to install ([a-z0-9._+-]+)$",
            r"^install ([a-z0-9._+-]+) package$",
        ]

        for pattern in install_patterns:
            match = re.match(pattern, text)

            if not match:
                continue

            package = match.group(1).strip()

            return cls._proposal(
                command=f"sudo apt install {package}",
                explanation=(
                    f"Installs the {package} package using Ubuntu's "
                    "APT package manager."
                ),
                concept="Package Management",
                risk="medium",
                requires_sudo=True,
            )

        # ====================================================
        # UPDATE PACKAGE LIST
        # ====================================================

        if text in {
            "update packages",
            "update package list",
            "update apt",
            "refresh packages",
            "refresh apt",
        }:
            return cls._proposal(
                command="sudo apt update",
                explanation=(
                    "Refreshes the package information available "
                    "from configured Ubuntu repositories."
                ),
                concept="Package Management",
                risk="medium",
                requires_sudo=True,
            )

        # ====================================================
        # WHO AM I
        # ====================================================

        if text in {
            "who am i",
            "show my user",
            "show current user",
            "what user am i",
        }:
            return cls._proposal(
                command="whoami",
                explanation="Shows the username of the current user.",
                concept="User Identity",
            )

        # ====================================================
        # SYSTEM INFORMATION
        # ====================================================

        if text in {
            "show system information",
            "show linux version",
            "what linux version am i using",
            "what version of linux am i using",
        }:
            return cls._proposal(
                command="uname -a",
                explanation=(
                    "Displays kernel and system information for the "
                    "current Linux environment."
                ),
                concept="System Information",
            )

        # ====================================================
        # DISK SPACE
        # ====================================================

        if text in {
            "show disk space",
            "check disk space",
            "how much disk space do i have",
            "how much storage do i have",
        }:
            return cls._proposal(
                command="df -h",
                explanation="Shows disk space usage in a human-readable format.",
                concept="Disk Management",
            )

        # ====================================================
        # MEMORY
        # ====================================================

        if text in {
            "show memory",
            "check memory",
            "check ram",
            "how much ram do i have",
        }:
            return cls._proposal(
                command="free -h",
                explanation="Shows available and used system memory.",
                concept="System Resources",
            )

        # ====================================================
        # DO NOT GUESS
        # ====================================================

        return None
