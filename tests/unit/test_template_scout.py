"""Tests for the TemplateScout service."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from extractly.clients.gemini_client import FileRef
from extractly.models.template import MasterTemplate
from extractly.services.template_scout import TemplateScout


VALID_TEMPLATE_JSON = json.dumps({
    "document_type": "Certificate of Analysis",
    "sections": [
        {
            "name": "Header",
            "fields": [
                {"label": "Batch Number", "field_type": "text"},
                {"label": "Date", "field_type": "date"},
            ],
        },
        {
            "name": "Results",
            "fields": [
                {"label": "Assay", "field_type": "number"},
            ],
        },
    ],
})


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock GeminiClient."""
    client = MagicMock()
    client.upload_file.return_value = FileRef(
        name="files/sample", uri="https://uri/sample", display_name="sample"
    )
    return client


@pytest.fixture
def scout(mock_client: MagicMock) -> TemplateScout:
    """Create a TemplateScout with a mocked client."""
    return TemplateScout(client=mock_client)


class TestDiscover:
    """Tests for TemplateScout.discover."""

    def test_discover_success(
        self, scout: TemplateScout, mock_client: MagicMock, sample_pdf: Path
    ) -> None:
        """discover should return a MasterTemplate when AI returns valid JSON."""
        mock_client.analyze_document.return_value = VALID_TEMPLATE_JSON

        template = scout.discover(sample_pdf)

        assert template.document_type == "Certificate of Analysis"
        assert len(template.sections) == 2
        assert template.sections[0].name == "Header"
        assert len(template.sections[0].fields) == 2

    def test_discover_with_markdown_fences(
        self, scout: TemplateScout, mock_client: MagicMock, sample_pdf: Path
    ) -> None:
        """discover should handle JSON wrapped in markdown code fences."""
        mock_client.analyze_document.return_value = f"```json\n{VALID_TEMPLATE_JSON}\n```"

        template = scout.discover(sample_pdf)

        assert template.document_type == "Certificate of Analysis"

    def test_discover_invalid_json_raises(
        self, scout: TemplateScout, mock_client: MagicMock, sample_pdf: Path
    ) -> None:
        """discover should raise ValueError for non-JSON response."""
        mock_client.analyze_document.return_value = "This is not JSON at all"

        with pytest.raises(ValueError, match="Failed to parse AI response"):
            scout.discover(sample_pdf)

    def test_discover_wrong_structure_raises(
        self, scout: TemplateScout, mock_client: MagicMock, sample_pdf: Path
    ) -> None:
        """discover should raise ValueError when JSON doesn't match template schema."""
        mock_client.analyze_document.return_value = json.dumps({"wrong": "structure"})

        with pytest.raises(ValueError, match="does not match template structure"):
            scout.discover(sample_pdf)

    def test_discover_uploads_file(
        self, scout: TemplateScout, mock_client: MagicMock, sample_pdf: Path
    ) -> None:
        """discover should upload the sample file via the client."""
        mock_client.analyze_document.return_value = VALID_TEMPLATE_JSON

        scout.discover(sample_pdf)

        mock_client.upload_file.assert_called_once_with(sample_pdf)

    def test_discover_sends_prompt(
        self, scout: TemplateScout, mock_client: MagicMock, sample_pdf: Path
    ) -> None:
        """discover should call analyze_document with the file ref and a prompt."""
        mock_client.analyze_document.return_value = VALID_TEMPLATE_JSON

        scout.discover(sample_pdf)

        mock_client.analyze_document.assert_called_once()
        call_args = mock_client.analyze_document.call_args
        assert isinstance(call_args[0][0], FileRef)
        assert "sections" in call_args[0][1]  # prompt mentions sections


class TestSaveTemplate:
    """Tests for TemplateScout.save_template."""

    def test_save_creates_file(self, scout: TemplateScout, tmp_path: Path) -> None:
        """save_template should write a valid JSON file."""
        template = MasterTemplate.model_validate_json(VALID_TEMPLATE_JSON)
        output_path = tmp_path / "output" / "template.json"

        result = scout.save_template(template, output_path)

        assert result.exists()
        loaded = json.loads(result.read_text(encoding="utf-8"))
        assert loaded["document_type"] == "Certificate of Analysis"

    def test_save_creates_parent_dirs(self, scout: TemplateScout, tmp_path: Path) -> None:
        """save_template should create parent directories if they don't exist."""
        template = MasterTemplate.model_validate_json(VALID_TEMPLATE_JSON)
        output_path = tmp_path / "deep" / "nested" / "template.json"

        result = scout.save_template(template, output_path)

        assert result.exists()

    def test_save_roundtrip(self, scout: TemplateScout, tmp_path: Path) -> None:
        """Saved template should be loadable back as a MasterTemplate."""
        original = MasterTemplate.model_validate_json(VALID_TEMPLATE_JSON)
        output_path = tmp_path / "template.json"

        scout.save_template(original, output_path)

        loaded = MasterTemplate.model_validate_json(output_path.read_text(encoding="utf-8"))
        assert loaded == original
