"""Vision/OCR extraction engines.

Default pilot engine: the Claude (Anthropic) vision API, called from Django
(cureva-docs/04-architecture-and-stack.md). The engine sits behind the
`extraction_engine` field on intakes so it can be swapped without a data-model
change. The model never verifies or publishes — it only proposes; a human
confirms low-confidence fields (cureva-docs/03).

An injectable MockExtractor drives the golden-file tests and lets the pipeline
run end to end without the real API key.
"""
import base64
import json
import re
from abc import ABC, abstractmethod

from django.conf import settings

ENGINE_CLAUDE = "claude-vision-v1"
ENGINE_MOCK = "mock-v1"


class ExtractionError(Exception):
    """Raised when the extraction call fails (outage, rate limit, bad output).
    The pipeline moves the intake to `extraction_failed` and retries."""


class VisionExtractor(ABC):
    engine_name: str = "abstract"

    @abstractmethod
    def extract(self, images: list[bytes], template: dict) -> list[dict]:
        """Return one dict per register row:
        {"fields": {label: value, ...}, "confidence": {label: 0.0-1.0, ...}}
        keyed by the label text the model actually read on the page.
        """


class MockExtractor(VisionExtractor):
    """Returns preset rows — deterministic, for tests and local dev."""

    engine_name = ENGINE_MOCK

    def __init__(self, rows: list[dict], fail: bool = False):
        self._rows = rows
        self._fail = fail

    def extract(self, images, template):
        if self._fail:
            raise ExtractionError("Simulated extraction-provider failure.")
        return self._rows


class ClaudeVisionExtractor(VisionExtractor):
    """Reads a photographed register page with the Claude vision API."""

    engine_name = ENGINE_CLAUDE

    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.model = model or getattr(settings, "ANTHROPIC_VISION_MODEL", "claude-sonnet-5-5")
        self.api_key = api_key or settings.ANTHROPIC_API_KEY

    def _prompt(self, template: dict) -> str:
        fields = []
        for col in template["columns"]:
            aliases = ", ".join(col.get("aliases", []))
            fields.append(f"- {col['label']} (type: {col['type']}; also written as: {aliases})")
        field_list = "\n".join(fields)
        return (
            "You are reading a photographed maternal-health register page. Extract "
            "every data row you can see. For each row, return the value under the "
            "EXACT column header/label you see printed on the page (not a renamed "
            "field). Also return your confidence (0.0-1.0) that you read each value "
            "correctly. Leave a field out entirely if the cell is blank — never guess.\n\n"
            f"Expected columns on this register:\n{field_list}\n\n"
            'Respond with ONLY a JSON array, one object per row, shaped like:\n'
            '[{"fields": {"<label>": "<value>"}, "confidence": {"<label>": 0.0}}]'
        )

    def extract(self, images, template):
        if not self.api_key:
            raise ExtractionError("ANTHROPIC_API_KEY is not configured.")
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise ExtractionError("anthropic SDK not installed.") from exc

        client = anthropic.Anthropic(api_key=self.api_key)
        content = [{"type": "text", "text": self._prompt(template)}]
        for img in images:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": base64.b64encode(img).decode("ascii"),
                    },
                }
            )
        try:
            resp = client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": content}],
            )
        except Exception as exc:  # network/rate-limit/provider error
            raise ExtractionError(str(exc)) from exc

        text = "".join(block.text for block in resp.content if getattr(block, "type", None) == "text")
        return self._parse(text)

    @staticmethod
    def _parse(text: str) -> list[dict]:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            raise ExtractionError("Model did not return a JSON array.")
        try:
            data = json.loads(match.group())
        except json.JSONDecodeError as exc:
            raise ExtractionError(f"Could not parse model JSON: {exc}") from exc
        rows = []
        for row in data:
            rows.append({"fields": row.get("fields", {}), "confidence": row.get("confidence", {})})
        return rows


def default_extractor() -> VisionExtractor:
    """The configured default engine for real intakes."""
    return ClaudeVisionExtractor()
