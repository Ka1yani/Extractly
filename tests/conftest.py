"""Shared test fixtures for Extractly test suite."""

from pathlib import Path

import pytest


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory for tests."""
    output = tmp_path / "output"
    output.mkdir()
    return output


@pytest.fixture
def tmp_input_dir(tmp_path: Path) -> Path:
    """Create a temporary input directory with a dummy PDF for tests."""
    input_dir = tmp_path / "input_docs"
    input_dir.mkdir()
    return input_dir


@pytest.fixture
def sample_pdf(tmp_input_dir: Path) -> Path:
    """Create a minimal dummy PDF file for testing file operations."""
    pdf_path = tmp_input_dir / "sample.pdf"
    # Minimal valid PDF (just enough for file-existence checks)
    pdf_path.write_bytes(b"%PDF-1.4 minimal test content")
    return pdf_path
