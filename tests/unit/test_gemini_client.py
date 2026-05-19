"""Tests for the GeminiClient wrapper.

All Gemini API calls are mocked — no real API key or network needed.
We test that our wrapper correctly calls the SDK and handles responses.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass

import pytest

from extractly.clients.gemini_client import GeminiClient, FileRef


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_genai_client() -> MagicMock:
    """Create a mock of genai.Client."""
    return MagicMock()


@pytest.fixture
def client(mock_genai_client: MagicMock) -> GeminiClient:
    """Create a GeminiClient with a mocked underlying SDK client."""
    with patch("extractly.clients.gemini_client.genai.Client", return_value=mock_genai_client):
        return GeminiClient(api_key="test-key", model="gemini-2.5-flash")


@pytest.fixture
def sample_file_ref() -> FileRef:
    """A sample FileRef for testing."""
    return FileRef(name="files/abc123", uri="https://example.com/files/abc123", display_name="doc1")


# ---------------------------------------------------------------------------
# FileRef tests
# ---------------------------------------------------------------------------
class TestFileRef:
    """Tests for the FileRef dataclass."""

    def test_create_file_ref(self) -> None:
        """FileRef should store name, uri, and display_name."""
        ref = FileRef(name="files/123", uri="https://uri", display_name="my_doc")
        assert ref.name == "files/123"
        assert ref.uri == "https://uri"
        assert ref.display_name == "my_doc"

    def test_file_ref_is_frozen(self) -> None:
        """FileRef should be immutable."""
        ref = FileRef(name="files/123", uri="https://uri", display_name="doc")
        with pytest.raises(AttributeError):
            ref.name = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# upload_file tests
# ---------------------------------------------------------------------------
class TestUploadFile:
    """Tests for GeminiClient.upload_file."""

    def test_upload_file_success(
        self, client: GeminiClient, mock_genai_client: MagicMock, sample_pdf: Path
    ) -> None:
        """upload_file should return a FileRef on success."""
        mock_uploaded = MagicMock()
        mock_uploaded.name = "files/xyz"
        mock_uploaded.uri = "https://uri/xyz"
        mock_genai_client.files.upload.return_value = mock_uploaded

        ref = client.upload_file(sample_pdf)

        assert ref.name == "files/xyz"
        assert ref.uri == "https://uri/xyz"
        assert ref.display_name == "sample"
        mock_genai_client.files.upload.assert_called_once()

    def test_upload_file_not_found(self, client: GeminiClient) -> None:
        """upload_file should raise FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError, match="File not found"):
            client.upload_file(Path("/nonexistent/file.pdf"))


# ---------------------------------------------------------------------------
# analyze_document tests
# ---------------------------------------------------------------------------
class TestAnalyzeDocument:
    """Tests for GeminiClient.analyze_document."""

    def test_analyze_document_success(
        self,
        client: GeminiClient,
        mock_genai_client: MagicMock,
        sample_file_ref: FileRef,
    ) -> None:
        """analyze_document should return the model's text response."""
        mock_response = MagicMock()
        mock_response.text = '{"document_type": "Invoice"}'
        mock_genai_client.models.generate_content.return_value = mock_response

        result = client.analyze_document(sample_file_ref, "Analyze this")

        assert result == '{"document_type": "Invoice"}'
        mock_genai_client.models.generate_content.assert_called_once()

    def test_analyze_document_empty_response(
        self,
        client: GeminiClient,
        mock_genai_client: MagicMock,
        sample_file_ref: FileRef,
    ) -> None:
        """analyze_document should raise RuntimeError on empty response."""
        mock_response = MagicMock()
        mock_response.text = None
        mock_genai_client.models.generate_content.return_value = mock_response

        with pytest.raises(RuntimeError, match="Empty response"):
            client.analyze_document(sample_file_ref, "Analyze this")


# ---------------------------------------------------------------------------
# upload_jsonl tests
# ---------------------------------------------------------------------------
class TestUploadJsonl:
    """Tests for GeminiClient.upload_jsonl."""

    def test_upload_jsonl_success(
        self, client: GeminiClient, mock_genai_client: MagicMock, tmp_path: Path
    ) -> None:
        """upload_jsonl should return a FileRef on success."""
        jsonl_file = tmp_path / "batch.jsonl"
        jsonl_file.write_text('{"key": "req-1"}\n')

        mock_uploaded = MagicMock()
        mock_uploaded.name = "files/jsonl123"
        mock_uploaded.uri = "https://uri/jsonl123"
        mock_genai_client.files.upload.return_value = mock_uploaded

        ref = client.upload_jsonl(jsonl_file)

        assert ref.name == "files/jsonl123"
        mock_genai_client.files.upload.assert_called_once()

    def test_upload_jsonl_not_found(self, client: GeminiClient) -> None:
        """upload_jsonl should raise FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError, match="JSONL file not found"):
            client.upload_jsonl(Path("/nonexistent/batch.jsonl"))


# ---------------------------------------------------------------------------
# create_batch_job tests
# ---------------------------------------------------------------------------
class TestCreateBatchJob:
    """Tests for GeminiClient.create_batch_job."""

    def test_create_batch_job_returns_name(
        self,
        client: GeminiClient,
        mock_genai_client: MagicMock,
        sample_file_ref: FileRef,
    ) -> None:
        """create_batch_job should return the job name."""
        mock_job = MagicMock()
        mock_job.name = "batches/job123"
        mock_genai_client.batches.create.return_value = mock_job

        result = client.create_batch_job(sample_file_ref)

        assert result == "batches/job123"
        mock_genai_client.batches.create.assert_called_once()


# ---------------------------------------------------------------------------
# poll_batch_job tests
# ---------------------------------------------------------------------------
class TestPollBatchJob:
    """Tests for GeminiClient.poll_batch_job."""

    def test_poll_succeeds_immediately(
        self, client: GeminiClient, mock_genai_client: MagicMock
    ) -> None:
        """poll should return results when job succeeds on first poll."""
        mock_job = MagicMock()
        mock_job.state.name = "JOB_STATE_SUCCEEDED"
        mock_job.dest.file_name = "files/result123"
        mock_genai_client.batches.get.return_value = mock_job
        mock_genai_client.files.download.return_value = b'{"key": "req-1", "response": {}}\n'

        result = client.poll_batch_job("batches/job123", poll_interval=0)

        assert '"key": "req-1"' in result

    def test_poll_fails(self, client: GeminiClient, mock_genai_client: MagicMock) -> None:
        """poll should raise RuntimeError when job fails."""
        mock_job = MagicMock()
        mock_job.state.name = "JOB_STATE_FAILED"
        mock_job.error = "Some error"
        mock_genai_client.batches.get.return_value = mock_job

        with pytest.raises(RuntimeError, match="Batch job failed"):
            client.poll_batch_job("batches/job123", poll_interval=0)

    def test_poll_cancelled(self, client: GeminiClient, mock_genai_client: MagicMock) -> None:
        """poll should raise RuntimeError when job is cancelled."""
        mock_job = MagicMock()
        mock_job.state.name = "JOB_STATE_CANCELLED"
        mock_genai_client.batches.get.return_value = mock_job

        with pytest.raises(RuntimeError, match="cancelled"):
            client.poll_batch_job("batches/job123", poll_interval=0)

    def test_poll_expired(self, client: GeminiClient, mock_genai_client: MagicMock) -> None:
        """poll should raise RuntimeError when job expires."""
        mock_job = MagicMock()
        mock_job.state.name = "JOB_STATE_EXPIRED"
        mock_genai_client.batches.get.return_value = mock_job

        with pytest.raises(RuntimeError, match="expired"):
            client.poll_batch_job("batches/job123", poll_interval=0)

    def test_poll_timeout(self, client: GeminiClient, mock_genai_client: MagicMock) -> None:
        """poll should raise RuntimeError when timeout is reached."""
        mock_job = MagicMock()
        mock_job.state.name = "JOB_STATE_RUNNING"
        mock_genai_client.batches.get.return_value = mock_job

        with pytest.raises(RuntimeError, match="timed out"):
            client.poll_batch_job("batches/job123", poll_interval=0, timeout=0)

    def test_poll_no_result_file(self, client: GeminiClient, mock_genai_client: MagicMock) -> None:
        """poll should raise RuntimeError when succeeded but no result file."""
        mock_job = MagicMock()
        mock_job.state.name = "JOB_STATE_SUCCEEDED"
        mock_job.dest = None
        mock_genai_client.batches.get.return_value = mock_job

        with pytest.raises(RuntimeError, match="no result file"):
            client.poll_batch_job("batches/job123", poll_interval=0)
