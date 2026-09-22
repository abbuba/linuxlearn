import json
import urllib.request

from openai import OpenAI

from linuxlearn.context import TerminalContext


class LLMClient:
    """
    Context-aware LLM client.

    The TerminalContext is owned by LinuxLearn.
    The model receives a read-only context packet for each request.
    """

    def __init__(
        self,
        config: dict,
        context: TerminalContext,
    ):
        self.config = config
        self.context = context

    # =========================================================
    # SYSTEM PROMPT
    # =========================================================

    def _get_system_prompt(
        self,
        user_request: str,
    ) -> str:
        world_state = (
            self.context.get_llm_context(
                user_request
            )
        )

        return f"""
You are LinuxLearn, a context-aware Linux terminal learning assistant.

Your job is to translate a beginner's natural-language Linux request
into a precise shell command while respecting the actual terminal state.

IMPORTANT:
LinuxLearn itself owns terminal state.
You only READ the supplied context.
Never invent a current directory, file, folder, or previous action.

<terminal_context>
{world_state}
</terminal_context>

RULES:

1. CURRENT DIRECTORY
The "current_directory" in terminal_context is authoritative for the
current LinuxLearn session.

If the user gives a relative path, interpret it relative to that
current directory unless the user clearly specifies another location.

2. FILESYSTEM GROUNDING
Use known_entities, resolved_references, filesystem information, and
recent successful actions when resolving references.

For phrases such as:
- it
- that
- this folder
- there
- the folder we just created
- the directory named X

use the supplied resolved_references whenever available.

Do not invent a path just because a name sounds plausible.

3. TERMINAL STATE
A normal subprocess cannot permanently remember "cd".

Therefore, when the user's request explicitly changes location:
- set "changes_cwd": true
- set "working_directory" to the intended final directory
- make the command correctly perform that operation.

For example, if the user is in ~/linuxlearn and asks:

"Go to the folder ab in desktop and create 100 folders"

and context says ~/Desktop/ab exists, a valid command may be:

cd "$HOME/Desktop/ab" && mkdir -p {{1..100}}

4. PATHS
Use $HOME when appropriate rather than inventing the user's username.

For example:
"$HOME/Desktop/ab"

is preferred over an invented:
"/home/someone/Desktop/ab"

5. SAFETY
Never bypass LinuxLearn's human confirmation step.

Do not use sudo unless it is genuinely required.

Commands that delete, overwrite, modify permissions, install software,
change networking, or otherwise affect the system should be represented
accurately so the security layer can inspect them.

6. TEACHING
The explanation must teach the Linux concept briefly.

7. OUTPUT
Return ONLY valid JSON.

Do not use Markdown.
Do not wrap JSON in ```json.

The JSON schema is:

{{
  "intent": "short description of the user's intended operation",
  "command": "exact bash command",
  "explanation": "beginner-friendly explanation",
  "concept": "core Linux concept",
  "risk": "low | medium | high",
  "requires_sudo": true,
  "changes_cwd": true,
  "working_directory": "absolute intended final working directory or null",
  "target_paths": ["relevant absolute or $HOME-based paths"],
  "created_paths": ["top-level paths created by this action"],
  "modified_paths": ["important paths modified by this action"],
  "deleted_paths": ["paths deleted by this action"]
}}

Use empty arrays when a field does not apply.

The user request is:

{user_request}
"""

    # =========================================================
    # PUBLIC QUERY
    # =========================================================

    def query(
        self,
        user_prompt: str,
    ) -> tuple[dict, str]:

        primary = self.config.get(
            "provider",
            "openai_compatible",
        )

        try:
            result = self._query_provider(
                provider=primary,
                user_prompt=user_prompt,
                backup=False,
            )

            return result, self._provider_badge(
                primary,
                backup=False,
            )

        except Exception as primary_error:

            backup = self.config.get(
                "backup_provider"
            )

            if not backup:
                raise primary_error

            try:
                result = self._query_provider(
                    provider=backup,
                    user_prompt=user_prompt,
                    backup=True,
                )

                return result, self._provider_badge(
                    backup,
                    backup=True,
                )

            except Exception as backup_error:
                raise RuntimeError(
                    "Primary and backup intelligence "
                    "providers failed.\n\n"
                    f"Primary: {primary_error}\n"
                    f"Backup: {backup_error}"
                ) from backup_error

    # =========================================================
    # PROVIDER ROUTER
    # =========================================================

    def _query_provider(
        self,
        provider: str,
        user_prompt: str,
        backup: bool,
    ) -> dict:

        if provider == "ollama":
            return self._query_ollama(
                user_prompt,
                backup=backup,
            )

        if provider == "openai_compatible":
            return self._query_openai_compatible(
                user_prompt,
                backup=backup,
            )

        raise ValueError(
            f"Unsupported LLM provider: {provider}"
        )

    # =========================================================
    # OLLAMA
    # =========================================================

    def _query_ollama(
        self,
        user_prompt: str,
        backup: bool = False,
    ) -> dict:

        if backup:
            base_url = self.config.get(
                "backup_ollama_base_url",
                "http://localhost:11434",
            )
            model = self.config.get(
                "backup_model"
            )
        else:
            base_url = self.config.get(
                "ollama_base_url",
                "http://localhost:11434",
            )
            model = self.config.get(
                "model",
                "qwen2.5-coder:1.5b",
            )

        if not model:
            raise ValueError(
                "No Ollama model configured."
            )

        base_url = base_url.rstrip("/")

        url = f"{base_url}/api/generate"

        payload = {
            "model": model,
            "system": self._get_system_prompt(
                user_prompt
            ),
            "prompt": user_prompt,
            "stream": False,
            "format": "json",
        }

        request = urllib.request.Request(
            url,
            data=json.dumps(
                payload
            ).encode("utf-8"),
            headers={
                "Content-Type":
                    "application/json"
            },
            method="POST",
        )

        with urllib.request.urlopen(
            request,
            timeout=60,
        ) as response:

            response_data = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

        raw_response = response_data.get(
            "response",
            "{}",
        )

        result = json.loads(
            raw_response
        )

        return self._normalize_result(
            result
        )

    # =========================================================
    # OPENAI-COMPATIBLE
    # =========================================================

    def _query_openai_compatible(
        self,
        user_prompt: str,
        backup: bool = False,
    ) -> dict:

        if backup:
            base_url = self.config.get(
                "backup_api_base_url",
                "https://api.groq.com/openai/v1",
            )
            api_key = self.config.get(
                "backup_api_key",
                "",
            ).strip()
            model = self.config.get(
                "backup_model",
                "openai/gpt-oss-120b",
            )
        else:
            base_url = self.config.get(
                "api_base_url",
                "https://api.groq.com/openai/v1",
            )
            api_key = self.config.get(
                "api_key",
                "",
            ).strip()
            model = self.config.get(
                "model",
                "openai/gpt-oss-120b",
            )

        if not api_key:
            raise ValueError(
                "Cloud API key is not configured."
            )

        if not model:
            raise ValueError(
                "Cloud model is not configured."
            )

        client = OpenAI(
            base_url=base_url,
            api_key=api_key,
        )

        response = (
            client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content":
                            self._get_system_prompt(
                                user_prompt
                            ),
                    },
                    {
                        "role": "user",
                        "content":
                            user_prompt,
                    },
                ],
                response_format={
                    "type":
                        "json_object"
                },
            )
        )

        content = (
            response
            .choices[0]
            .message
            .content
        )

        if not content:
            raise ValueError(
                "LLM returned an empty response."
            )

        result = json.loads(
            content
        )

        return self._normalize_result(
            result
        )

    # =========================================================
    # OUTPUT NORMALIZATION
    # =========================================================

    def _normalize_result(
        self,
        result: dict,
    ) -> dict:

        if not isinstance(result, dict):
            raise ValueError(
                "LLM response is not a JSON object."
            )

        result.setdefault(
            "intent",
            "unknown",
        )

        result.setdefault(
            "command",
            "",
        )

        result.setdefault(
            "explanation",
            "",
        )

        result.setdefault(
            "concept",
            "General Linux",
        )

        result.setdefault(
            "risk",
            "low",
        )

        result.setdefault(
            "requires_sudo",
            False,
        )

        result.setdefault(
            "changes_cwd",
            False,
        )

        result.setdefault(
            "working_directory",
            None,
        )

        for key in [
            "target_paths",
            "created_paths",
            "modified_paths",
            "deleted_paths",
        ]:
            value = result.get(key)

            if value is None:
                result[key] = []

            elif isinstance(
                value,
                str,
            ):
                result[key] = [value]

            elif not isinstance(
                value,
                list,
            ):
                result[key] = []

        # Normalize risk.
        risk = str(
            result.get(
                "risk",
                "low",
            )
        ).lower()

        if risk not in {
            "low",
            "medium",
            "high",
        }:
            risk = "medium"

        result["risk"] = risk

        result["requires_sudo"] = bool(
            result.get(
                "requires_sudo",
                False,
            )
        )

        result["changes_cwd"] = bool(
            result.get(
                "changes_cwd",
                False,
            )
        )

        return result

    @staticmethod
    def _provider_badge(
        provider: str,
        backup: bool,
    ) -> str:

        suffix = " BACKUP" if backup else ""

        if provider == "ollama":
            return f"💻 LOCAL OLLAMA{suffix}"

        return f"☁️ CLOUD API (Groq){suffix}"