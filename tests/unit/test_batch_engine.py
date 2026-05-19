"""Tests for the BatchEngine service."""

import json
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from extractly.clients.gemini_client import FileRef
from extractly.models.template import MasterTemplate, Section, Field
from extractly.models.extraction import ExtractedDocument
from extractly.services.batch_engine import BatchEngine, _build_extraction_prompt


@pytest.fixture
def sample_template() -> MasterTemplate:
    """A sample MasterTemplate for testing."""
    return MasterTemplate(
        document_type="Certificate of Analysis",
        sections=[
            Section(
                name="Header",
                fields=[
                    Field(label="Batch Number", field_type="text"),
                    Field(label="Date", field_type="date"),
                ],
            ),
        ],
    )


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock GeminiClient."""
    return MagicMock()


@pytest.fixture
def engine(mock_client: MagicMock) -> BatchEngine:
    """Create a BatchEngine with a mocked client."""
    return BatchEngine(client=mock_client, poll_interval=0, timeout=60)


class TestBuildExtractionPrompt:
    """Tests for the extraction prompt builder."""

    def test_prompt_contains_template_json(self, sample_template: MasterTemplate) -> None:
        """The prompt should embed the template JSON."""
        prompt = _build_extraction_prompt(sample_template)
        assert "Batch Number" in prompt
        assert "Certificate of Analysis" in prompt

    def test_prompt_instructs_json_output(self, sample_template: MasterTemplate) -> None:
        """The prompt should instruct the model to return JSON."""
        prompt = _build_extraction_prompt(sample_template)
        assert "JSON" in prompt

    def test_prompt_mentions_handwritten(self, sample_template: MasterTemplate) -> None:
        """The prompt should mention handwritten content handling."""
        prompt = _build_extraction_prompt(sample_template)
        assert "handwritten" in prompt.lower()


class TestDiscoverPdfs:
    """Tests for BatchEngine._discover_pdfs."""

    def test_finds_pdfs(self, engine: BatchEngine, tmp_input_dir: Path) -> None:
        """Should find PDF files in directory."""
        (tmp_input_dir / "a.pdf").write_bytes(b"pdf")
        (tmp_input_dir / "b.pdf").write_bytes(b"pdf")
        (tmp_input_dir / "c.txt").write_bytes(b"txt")  # Not a PDF

        pdfs = engine._discover_pdfs(tmp_input_dir)
        assert len(pdfs) == 2
        assert all(p.suffix == ".pdf" for p in pdfs)

    def test_empty_dir_raises(self, engine: BatchEngine, tmp_input_dir: Path) -> None:
        """Should raise FileNotFoundError when no PDFs exist."""
        with pytest.raises(FileNotFoundError, match="No PDF files"):
            engine._discover_pdfs(tmp_input_dir)

    def test_missing_dir_raises(self, engine: BatchEngine) -> None:
        """Should raise FileNotFoundError for non-existent directory."""
        with pytest.raises(FileNotFoundError, match="Input directory not found"):
            engine._discover_pdfs(Path("/nonexistent/dir"))

    def test_pdfs_are_sorted(self, engine: BatchEngine, tmp_input_dir: Path) -> None:
        """PDFs should be returned in sorted order."""
        (tmp_input_dir / "z.pdf").write_bytes(b"pdf")
        (tmp_input_dir / "a.pdf").write_bytes(b"pdf")

        pdfs = engine._discover_pdfs(tmp_input_dir)
        assert pdfs[0].name == "a.pdf"
        assert pdfs[1].name == "z.pdf"


class TestBuildJsonl:
    """Tests for BatchEngine._build_jsonl."""

    def test_creates_jsonl_file(
        self, engine: BatchEngine, sample_template: MasterTemplate, tmp_output_dir: Path
    ) -> None:
        """Should create a JSONL file with one line per file ref."""
        refs = [
            FileRef(name="files/1", uri="https://uri/1", display_name="doc1"),
            FileRef(name="files/2", uri="https://uri/2", display_name="doc2"),
        ]

        jsonl_path = engine._build_jsonl(refs, sample_template, tmp_output_dir)

        assert jsonl_path.exists()
        lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

    def test_jsonl_line_format(
        self, engine: BatchEngine, sample_template: MasterTemplate, tmp_output_dir: Path
    ) -> None:
        """Each JSONL line should have key and request with file_data + text."""
        refs = [FileRef(name="files/1", uri="https://uri/1", display_name="doc1")]

        jsonl_path = engine._build_jsonl(refs, sample_template, tmp_output_dir)

        line = json.loads(jsonl_path.read_text(encoding="utf-8").strip())
        assert line["key"] == "doc1"
        parts = line["request"]["contents"][0]["parts"]
        assert parts[0]["file_data"]["file_uri"] == "https://uri/1"
        assert "Batch Number" in parts[1]["text"]


class TestParseResults:
    """Tests for BatchEngine._parse_results."""

    def test_parse_valid_results(self, engine: BatchEngine) -> None:
        """Should parse valid batch results into ExtractedDocuments."""
        refs = [FileRef(name="files/1", uri="https://uri/1", display_name="doc1")]
        result_line = json.dumps({
            "key": "doc1",
            "response": {
                "candidates": [{
                    "content": {
                        "parts": [{
                            "text": json.dumps({
                                "sections": [{
                                    "name": "Header",
                                    "fields": {"Batch Number": "B-001"}
                                }]
                            })
                        }]
                    }
                }]
            }
        })

        docs = engine._parse_results(result_line, refs)

        assert len(docs) == 1
        assert docs[0].source_filename == "doc1.pdf"
        assert docs[0].get_field_value("Header", "Batch Number") == "B-001"

    def test_parse_malformed_json_graceful(self, engine: BatchEngine) -> None:
        """Should handle unparseable result lines gracefully."""
        refs = [FileRef(name="files/1", uri="https://uri/1", display_name="doc1")]

        docs = engine._parse_results("not json at all", refs)

        assert len(docs) == 0

    def test_parse_missing_response_text(self, engine: BatchEngine) -> None:
        """Should handle missing text in response gracefully."""
        refs = [FileRef(name="files/1", uri="https://uri/1", display_name="doc1")]
        result_line = json.dumps({"key": "doc1", "response": {"candidates": []}})

        docs = engine._parse_results(result_line, refs)

        assert len(docs) == 1
        assert docs[0].sections == []


class TestParseExtractionJson:
    """Tests for BatchEngine._parse_extraction_json."""

    def test_parse_valid_json(self, engine: BatchEngine) -> None:
        """Should parse valid extraction JSON."""
        raw = json.dumps({
            "sections": [{"name": "Header", "fields": {"Date": "2024-01-15"}}]
        })

        doc = engine._parse_extraction_json(raw, "test.pdf")

        assert doc.source_filename == "test.pdf"
        assert doc.get_field_value("Header", "Date") == "2024-01-15"

    def test_parse_with_markdown_fences(self, engine: BatchEngine) -> None:
        """Should handle JSON wrapped in markdown code fences."""
        raw = '```json\n{"sections": [{"name": "A", "fields": {"X": "1"}}]}\n```'

        doc = engine._parse_extraction_json(raw, "test.pdf")

        assert doc.get_field_value("A", "X") == "1"

    def test_parse_invalid_json_returns_empty(self, engine: BatchEngine) -> None:
        """Should return empty doc for unparseable JSON."""
        doc = engine._parse_extraction_json("not json", "test.pdf")

        assert doc.source_filename == "test.pdf"
        assert doc.sections == []
