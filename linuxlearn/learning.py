"""Data-driven content for LinuxLearn's introductory course."""

COURSE_ONE = {
    "title": "Getting Comfortable with Linux",
    "lessons": [
        {
            "title": "The Terminal",
            "explanation": (
                "A terminal is where you interact with the computer by text. "
                "The shell reads commands and asks Linux to run them. The prompt "
                "shows the shell is ready; its text often includes your user and location."
            ),
            "examples": [
                {
                    "command": 'echo "Hello Linux"',
                    "why": "`echo` prints the text you give it.",
                    "after": "The shell received your command, executed `echo`, and printed the result.",
                }
            ],
        },
        {
            "title": "Where Am I?",
            "explanation": "Your shell keeps a current working directory. `pwd` prints its full path.",
            "examples": [
                {
                    "command": "pwd",
                    "why": "`pwd` asks Linux for the current working directory.",
                    "after": "Linux reports your current path as "
                    "{cwd}.",
                }
            ],
        },
        {
            "title": "What Is Here?",
            "explanation": "`ls` lists visible items here. Once you have tried it, `ls -la` also shows hidden items and details.",
            "examples": [
                {
                    "command": "ls",
                    "why": "`ls` lists the visible contents of this directory.",
                    "after": "Those names came from the current directory on your filesystem.",
                },
                {
                    "command": "ls -la",
                    "why": "`-l` adds details and `-a` includes hidden names beginning with a dot.",
                    "after": "The listing includes hidden entries and extra file details.",
                },
            ],
        },
        {
            "title": "Moving Around",
            "explanation": "Use `cd <directory>` to enter a directory. `cd ..` moves to its parent; `cd ~` returns home. A relative name is resolved from where you are now.",
            "examples": [
                {
                    "command": "cd <directory>",
                    "why": "Replace `<directory>` with a directory name shown by `ls`.",
                    "after": "Your current directory is now {cwd}.",
                },
                {
                    "command": "cd ..",
                    "why": "`..` names the parent directory.",
                    "after": "You moved to the parent directory: {cwd}.",
                },
                {
                    "command": "cd ~",
                    "why": "`~` is shorthand for your home directory.",
                    "after": "You returned to your home directory: {cwd}.",
                },
            ],
        },
        {
            "title": "Paths",
            "explanation": "An absolute path starts at `/` and names one location directly. A relative path starts from your current directory. You will enter one directory with a relative path, then reach that same directory with its absolute path.",
            "examples": [
                {
                    "command": "pwd",
                    "why": "This gives the absolute path of the directory you are in.",
                    "after": "The absolute path is {cwd}.",
                },
                {
                    "command": "cd <relative path>",
                    "why": "This directory name is relative to where you are now.",
                    "after": "Linux resolved that path to {cwd}.",
                },
                {
                    "command": "cd <absolute path>",
                    "why": "This full path starts at `/` and reaches the same directory directly.",
                    "after": "Both paths reached {cwd}.",
                },
            ],
        },
    ],
}
