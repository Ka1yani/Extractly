"""Task 1: Structural Discovery — The Template Scout.

Analyzes a single sample document to discover its visual structure
and produce a Master JSON Template defining sections and fields.

Usage:
    scout = TemplateScout(gemini_client)
    template = scout.discover(Path("sample.pdf"))
    scout.save_template(template, Path("output/master_template.json"))
"""

import json
import logging
from pathlib import Path

from extractly.clients.gemini_client import GeminiClient
from extractly.models.template import MasterTemplate

logger = logging.getLogger(__name__)

# The prompt instructs Gemini to analyze the document's visual layout.
# Emphasis on handwritten/scanned content since 90% of docs are scanned forms.
DISCOVERY_PROMPT = """Analyze this document's visual layout and structure carefully.
This may be a scanned document with handwritten content — focus on the FORM STRUCTURE,
not the handwritten values.

Identify all logical sections, groups, or boxes visible in the document
(e.g., Header, Patient Information, Test Results, Footer, Shipping Details).

For each section, list every FIELD LABEL you can see (the printed labels, not handwritten values).
Classify each field's expected data type.

Return ONLY a valid JSON object with this exact structure (no markdown, no explanation):
{
    "document_type": "<what type of document this is>",
    "sections": [
        {
            "name": "<section name>",
            "fields": [
                {"label": "<field label text>", "field_type": "<text|number|date|table>"}
            ]
        }
    ]
}"""


class TemplateScout:
    """Discovers document structure from a sample PDF.

    This service uploads a sample document to Gemini, asks it to
    analyze the visual layout, and parses the response into a
    MasterTemplate.

    Args:
        client: A GeminiClient instance for API communication.
    """

    def __init__(self, client: GeminiClient) -> None:
        self._client = client

    def discover(self, sample_path: Path) -> MasterTemplate:
        """Analyze a sample document and produce a MasterTemplate.

        Args:
            sample_path: Path to the sample PDF document.

        Returns:
            A MasterTemplate describing the document's structure.

        Raises:
            FileNotFoundError: If the sample file doesn't exist.
            ValueError: If the AI response cannot be parsed as a valid template.
        """
        logger.info("Starting structural discovery on: %s", sample_path.name)

        # Step 1: Upload the sample document
        file_ref = self._client.upload_file(sample_path)

        # Step 2: Ask Gemini to analyze the structure
        raw_response = self._client.analyze_document(file_ref, DISCOVERY_PROMPT)

        # Step 3: Parse the JSON response into a MasterTemplate
        template = self._parse_response(raw_response)

        logger.info(
            "Discovered template: %s with %d sections",
            template.document_type,
            len(template.sections),
        )
        return template

    def _parse_response(self, raw_response: str) -> MasterTemplate:
        """Parse the AI's raw text response into a MasterTemplate.

        Handles common issues like markdown code fences around JSON.

        Args:
            raw_response: The raw text from Gemini's response.

        Returns:
            A validated MasterTemplate.

        Raises:
            ValueError: If the response is not valid JSON or doesn't
                match the expected template structure.
        """
        # Strip markdown code fences if present (```json ... ```)
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            # Remove first line (```json) and last line (```)
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1]).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse AI response as JSON: {e}\nRaw response:\n{raw_response}"
            ) from e

        try:
            return MasterTemplate.model_validate(data)
        except Exception as e:
            raise ValueError(
                f"AI response JSON does not match template structure: {e}\nParsed data:\n{data}"
            ) from e

    def save_template(self, template: MasterTemplate, output_path: Path) -> Path:
        """Save a MasterTemplate to a JSON file.

        Args:
            template: The template to save.
            output_path: Path where the JSON file should be written.

        Returns:
            The path where the file was saved.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            template.model_dump_json(indent=2),
            encoding="utf-8",
        )
        logger.info("Template saved to: %s", output_path)
        return output_path
