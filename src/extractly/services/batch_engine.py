"""Task 2: Scalable Extraction — The Batch Engine.

Uploads all target documents, builds a JSONL batch file referencing
the Master Template, submits it to the Gemini Batch API, and parses
the results into ExtractedDocument objects.

Usage:
    engine = BatchEngine(gemini_client)
    documents = engine.extract(
        input_dir=Path("input_docs"),
        template=my_template,
        output_dir=Path("output"),
    )
"""

import json
import logging
from pathlib import Path

from extractly.clients.gemini_client import GeminiClient, FileRef
from extractly.models.template import MasterTemplate
from extractly.models.extraction import ExtractedDocument, ExtractedSection

logger = logging.getLogger(__name__)


def _build_extraction_prompt(template: MasterTemplate) -> str:
    """Build the extraction prompt that instructs Gemini how to extract data.

    Args:
        template: The MasterTemplate defining what to extract.

    Returns:
        A prompt string containing the template structure.
    """
    template_json = template.model_dump_json(indent=2)
    return f"""Extract data from this document following the exact structure below.
This may be a scanned document with handwritten content — read all handwritten
values carefully.

For each section and field listed in the template, find the corresponding
value in the document. If a field is not found or not applicable, use an
empty string.

Template Structure:
{template_json}

Return ONLY a valid JSON object with this exact structure (no markdown, no explanation):
{{
    "sections": [
        {{
            "name": "<section name from template>",
            "fields": {{"<label>": "<extracted value>", ...}}
        }}
    ]
}}"""


class BatchEngine:
    """Processes multiple documents using the Gemini Batch API.

    This service handles the full extraction pipeline:
    1. Discover PDF files in the input directory
    2. Upload each PDF to the Files API
    3. Build a JSONL batch request file
    4. Submit the batch job
    5. Poll for completion
    6. Parse results into ExtractedDocument objects

    Args:
        client: A GeminiClient instance for API communication.
        poll_interval: Seconds between batch status checks.
        timeout: Maximum seconds to wait for batch completion.
    """

    def __init__(
        self,
        client: GeminiClient,
        poll_interval: int = 30,
        timeout: int = 86400,
    ) -> None:
        self._client = client
        self._poll_interval = poll_interval
        self._timeout = timeout

    def extract(
        self,
        input_dir: Path,
        template: MasterTemplate,
        output_dir: Path,
    ) -> list[ExtractedDocument]:
        """Run the full batch extraction pipeline.

        Args:
            input_dir: Directory containing PDF documents to process.
            template: The MasterTemplate defining extraction structure.
            output_dir: Directory for intermediate files (JSONL).

        Returns:
            List of ExtractedDocument objects, one per input document.

        Raises:
            FileNotFoundError: If input_dir doesn't exist or has no PDFs.
            RuntimeError: If the batch job fails.
        """
        # Step 1: Find all PDFs
        pdf_files = self._discover_pdfs(input_dir)
        logger.info("Found %d PDF files in %s", len(pdf_files), input_dir)

        # Step 2: Upload all PDFs and collect references
        file_refs = self._upload_all(pdf_files)

        # Step 3: Build JSONL batch input file
        jsonl_path = self._build_jsonl(file_refs, template, output_dir)

        # Step 4: Upload JSONL and create batch job
        jsonl_ref = self._client.upload_jsonl(jsonl_path)
        job_name = self._client.create_batch_job(jsonl_ref)

        # Step 5: Poll until completion
        result_content = self._client.poll_batch_job(
            job_name,
            poll_interval=self._poll_interval,
            timeout=self._timeout,
        )

        # Step 6: Parse results
        documents = self._parse_results(result_content, file_refs)
        logger.info("Successfully extracted data from %d documents", len(documents))

        return documents

    def _discover_pdfs(self, input_dir: Path) -> list[Path]:
        """Find all PDF files in the input directory.

        Args:
            input_dir: Directory to search.

        Returns:
            Sorted list of PDF file paths.

        Raises:
            FileNotFoundError: If directory doesn't exist or has no PDFs.
        """
        if not input_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")

        pdfs = sorted(input_dir.glob("*.pdf"))

        if not pdfs:
            raise FileNotFoundError(f"No PDF files found in: {input_dir}")

        return pdfs

    def _upload_all(self, pdf_files: list[Path]) -> list[FileRef]:
        """Upload all PDF files to the Gemini Files API.

        Args:
            pdf_files: List of PDF file paths.

        Returns:
            List of FileRef objects in the same order as input.
        """
        refs: list[FileRef] = []
        for i, pdf_path in enumerate(pdf_files, start=1):
            logger.info("Uploading [%d/%d]: %s", i, len(pdf_files), pdf_path.name)
            ref = self._client.upload_file(pdf_path)
            refs.append(ref)
        return refs

    def _build_jsonl(
        self,
        file_refs: list[FileRef],
        template: MasterTemplate,
        output_dir: Path,
    ) -> Path:
        """Build a JSONL batch input file pairing each document with the extraction prompt.

        Each line in the JSONL follows the Gemini Batch API format:
        {"key": "<filename>", "request": {"contents": [...]}}

        Args:
            file_refs: List of uploaded file references.
            template: The MasterTemplate for extraction instructions.
            output_dir: Directory to write the JSONL file.

        Returns:
            Path to the generated JSONL file.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        jsonl_path = output_dir / "batch_requests.jsonl"
        prompt = _build_extraction_prompt(template)

        with open(jsonl_path, "w", encoding="utf-8") as f:
            for ref in file_refs:
                request_line = {
                    "key": ref.display_name,
                    "request": {
                        "contents": [
                            {
                                "parts": [
                                    {
                                        "file_data": {
                                            "mime_type": "application/pdf",
                                            "file_uri": ref.uri,
                                        }
                                    },
                                    {"text": prompt},
                                ],
                                "role": "user",
                            }
                        ]
                    },
                }
                f.write(json.dumps(request_line) + "\n")

        logger.info("JSONL batch file written: %s (%d requests)", jsonl_path, len(file_refs))
        return jsonl_path

    def _parse_results(
        self,
        result_content: str,
        file_refs: list[FileRef],
    ) -> list[ExtractedDocument]:
        """Parse the batch job result JSONL into ExtractedDocument objects.

        Args:
            result_content: Raw JSONL string from the batch job result file.
            file_refs: Original file references for mapping keys to filenames.

        Returns:
            List of ExtractedDocument objects.
        """
        # Build a key→filename lookup
        key_to_filename: dict[str, str] = {
            ref.display_name: f"{ref.display_name}.pdf" for ref in file_refs
        }

        documents: list[ExtractedDocument] = []

        for line in result_content.strip().splitlines():
            if not line.strip():
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Skipping unparseable result line: %s", line[:100])
                continue

            key = entry.get("key", "unknown")
            filename = key_to_filename.get(key, f"{key}.pdf")

            # Extract the text from the response
            response_data = entry.get("response", {})
            try:
                text = response_data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError, TypeError):
                logger.warning("No text in response for key: %s", key)
                documents.append(
                    ExtractedDocument(source_filename=filename, sections=[])
                )
                continue

            # Parse the extracted JSON
            doc = self._parse_extraction_json(text, filename)
            documents.append(doc)

        return documents

    def _parse_extraction_json(
        self, raw_text: str, filename: str
    ) -> ExtractedDocument:
        """Parse a single document's extraction response JSON.

        Args:
            raw_text: The raw JSON text from Gemini's response.
            filename: The source filename for the document.

        Returns:
            An ExtractedDocument with parsed sections and fields.
        """
        # Strip markdown fences if present
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1]).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse extraction JSON for %s", filename)
            return ExtractedDocument(source_filename=filename, sections=[])

        sections: list[ExtractedSection] = []
        for section_data in data.get("sections", []):
            sections.append(
                ExtractedSection(
                    name=section_data.get("name", "Unknown"),
                    fields=section_data.get("fields", {}),
                )
            )

        return ExtractedDocument(source_filename=filename, sections=sections)
