import os
import subprocess
import shlex

HIGH_RISK_PATTERNS = [
    "rm -rf /", "rm -rf /*", "mkfs", "dd if=/dev/zero", 
    ":(){ :|:& };:", "> /dev/sda", "chmod -R 777 /",
    "chown -R"
]

class SecurityValidator:
    @staticmethod
    def is_blocked(command: str) -> tuple[bool, str]:
        cmd_lower = command.lower().strip()
        for pattern in HIGH_RISK_PATTERNS:
            if pattern in cmd_lower:
                return True, f"Blocked high-risk pattern detected: '{pattern}'"
        return False, ""

    @staticmethod
    def execute(command: str) -> bool:
        # Final safety net before subprocess
        blocked, reason = SecurityValidator.is_blocked(command)
        if blocked:
            return False

        try:
            result = subprocess.run(
                command,
                shell=True,
                executable="/bin/bash",
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"\n[Exit status {e.returncode}]")
            return False
        except Exception as e:
            print(f"\nExecution error: {e}")
            return False