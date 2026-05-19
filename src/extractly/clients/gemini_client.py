"""Thin wrapper around the Google GenAI SDK.

Separates I/O (API calls) from business logic so that services
can be tested with a mock client. Each method does ONE thing.

Usage:
    client = GeminiClient(api_key="...", model="gemini-2.5-flash")
    file_ref = client.upload_file(Path("doc.pdf"))
    response = client.analyze_document(file_ref, "Describe this document")
"""

import json
import logging
import time
from pathlib import Path
from dataclasses import dataclass, field

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FileRef:
    """Reference to a file uploaded to the Gemini Files API.

    Attributes:
        name: Gemini-assigned file identifier (e.g., "files/abc123").
        uri: Full URI for referencing in prompts.
        display_name: Human-readable name.
    """

    name: str
    uri: str
    display_name: str


class GeminiClient:
    """Thin wrapper around the Google GenAI SDK.

    This class handles all direct communication with the Gemini API.
    Business logic belongs in the service layer, not here.

    Args:
        api_key: Gemini API key.
        model: Model name to use for generation (default: gemini-2.5-flash).
    """

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def upload_file(self, file_path: Path) -> FileRef:
        """Upload a file to the Gemini Files API.

        Args:
            file_path: Path to the local file to upload.

        Returns:
            A FileRef with the Gemini-assigned name and URI.

        Raises:
            FileNotFoundError: If the file does not exist.
            RuntimeError: If the upload fails.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info("Uploading file: %s", file_path.name)

        uploaded = self._client.files.upload(
            file=str(file_path),
            config=types.UploadFileConfig(
                display_name=file_path.stem,
                mime_type="application/pdf",
            ),
        )

        if not uploaded.name or not uploaded.uri:
            raise RuntimeError("Gemini API returned a file without a name or URI")

        ref = FileRef(
            name=uploaded.name,
            uri=uploaded.uri,
            display_name=file_path.stem,
        )
        logger.info("Uploaded: %s → %s", file_path.name, ref.name)
        return ref

    def analyze_document(self, file_ref: FileRef, prompt: str) -> str:
        """Send a prompt about an uploaded document and return the response text.

        Args:
            file_ref: Reference to the uploaded file.
            prompt: The instruction/question to send with the document.

        Returns:
            The model's text response.

        Raises:
            RuntimeError: If the API call fails or returns no content.
        """
        logger.info("Analyzing document: %s", file_ref.display_name)

        response = self._client.models.generate_content(
            model=self._model,
            contents=[
                types.Part.from_uri(file_uri=file_ref.uri, mime_type="application/pdf"),
                prompt,
            ],
        )

        if not response.text:
            raise RuntimeError(f"Empty response for document: {file_ref.display_name}")

        return response.text

    def upload_jsonl(self, jsonl_path: Path) -> FileRef:
        """Upload a JSONL batch input file to the Gemini Files API.

        Args:
            jsonl_path: Path to the local .jsonl file.

        Returns:
            A FileRef for the uploaded JSONL file.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        if not jsonl_path.exists():
            raise FileNotFoundError(f"JSONL file not found: {jsonl_path}")

        logger.info("Uploading JSONL batch file: %s", jsonl_path.name)

        uploaded = self._client.files.upload(
            file=str(jsonl_path),
            config=types.UploadFileConfig(
                display_name=jsonl_path.stem,
                mime_type="jsonl",
            ),
        )

        if not uploaded.name or not uploaded.uri:
            raise RuntimeError("Gemini API returned a JSONL file without a name or URI")

        return FileRef(
            name=uploaded.name,
            uri=uploaded.uri,
            display_name=jsonl_path.stem,
        )

    def create_batch_job(self, jsonl_file_ref: FileRef) -> str:
        """Submit a batch job using an uploaded JSONL file.

        Args:
            jsonl_file_ref: Reference to the uploaded JSONL input file.

        Returns:
            The batch job name/ID for polling.
        """
        logger.info("Creating batch job from: %s", jsonl_file_ref.name)

        batch_job = self._client.batches.create(
            model=self._model,
            src=jsonl_file_ref.name,
            config={"display_name": f"extractly-batch-{jsonl_file_ref.display_name}"},
        )

        if not batch_job.name:
            raise RuntimeError("Gemini API created a batch job without a name")

        logger.info("Batch job created: %s", batch_job.name)
        return batch_job.name

    def poll_batch_job(
        self,
        job_name: str,
        poll_interval: int = 30,
        timeout: int = 86400,
    ) -> str:
        """Poll a batch job until completion and return the result file content.

        Args:
            job_name: The batch job name returned by create_batch_job.
            poll_interval: Seconds between status checks.
            timeout: Maximum seconds to wait before giving up.

        Returns:
            The result file content as a UTF-8 string (JSONL format).

        Raises:
            RuntimeError: If the job fails, is cancelled, or times out.
        """
        completed_states = {
            "JOB_STATE_SUCCEEDED",
            "JOB_STATE_FAILED",
            "JOB_STATE_CANCELLED",
            "JOB_STATE_EXPIRED",
        }

        logger.info("Polling batch job: %s", job_name)
        elapsed = 0

        while elapsed < timeout:
            job = self._client.batches.get(name=job_name)
            state = job.state.name if job.state else "UNKNOWN"

            if state in completed_states:
                break

            logger.info("Job state: %s (elapsed: %ds)", state, elapsed)
            time.sleep(poll_interval)
            elapsed += poll_interval
        else:
            raise RuntimeError(f"Batch job timed out after {timeout}s: {job_name}")

        if state == "JOB_STATE_FAILED":
            raise RuntimeError(f"Batch job failed: {job_name} — {job.error}")

        if state == "JOB_STATE_CANCELLED":
            raise RuntimeError(f"Batch job was cancelled: {job_name}")

        if state == "JOB_STATE_EXPIRED":
            raise RuntimeError(f"Batch job expired: {job_name}")

        # JOB_STATE_SUCCEEDED — download results
        if job.dest and job.dest.file_name:
            logger.info("Downloading results from: %s", job.dest.file_name)
            content_bytes = self._client.files.download(file=job.dest.file_name)
            return content_bytes.decode("utf-8")

        raise RuntimeError(f"Batch job succeeded but no result file found: {job_name}")
