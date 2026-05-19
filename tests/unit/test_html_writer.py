"""Tests for the HtmlWriter service."""

from pathlib import Path

import pytest

from extractly.models.template import MasterTemplate, Section, Field
from extractly.models.extraction import ExtractedDocument, ExtractedSection
from extractly.services.html_writer import HtmlWriter


@pytest.fixture
def template() -> MasterTemplate:
    return MasterTemplate(
        document_type="Certificate",
        sections=[
            Section(name="Header", fields=[Field(label="Batch No"), Field(label="Date", field_type="date")]),
            Section(name="Results", fields=[Field(label="Assay", field_type="number")]),
        ],
    )


@pytest.fixture
def doc() -> ExtractedDocument:
    return ExtractedDocument(source_filename="doc1.pdf", sections=[
        ExtractedSection(name="Header", fields={"Batch No": "B-001", "Date": "2024-01-15"}),
        ExtractedSection(name="Results", fields={"Assay": "99.2%"}),
    ])


@pytest.fixture
def writer() -> HtmlWriter:
    return HtmlWriter()


class TestHtmlWriter:
    def test_creates_html_file(self, writer, doc, template, tmp_output_dir):
        paths = writer.write_all([doc], template, tmp_output_dir)
        assert len(paths) == 1
        assert paths[0].exists()
        assert paths[0].suffix == ".html"

    def test_filename_matches_source(self, writer, doc, template, tmp_output_dir):
        paths = writer.write_all([doc], template, tmp_output_dir)
        assert paths[0].name == "doc1.html"

    def test_contains_fieldsets(self, writer, doc, template, tmp_output_dir):
        paths = writer.write_all([doc], template, tmp_output_dir)
        html_content = paths[0].read_text(encoding="utf-8")
        assert "<fieldset>" in html_content
        assert "<legend>Header</legend>" in html_content
        assert "<legend>Results</legend>" in html_content

    def test_contains_field_values(self, writer, doc, template, tmp_output_dir):
        paths = writer.write_all([doc], template, tmp_output_dir)
        html_content = paths[0].read_text(encoding="utf-8")
        assert 'value="B-001"' in html_content
        assert 'value="99.2%"' in html_content

    def test_inputs_are_readonly(self, writer, doc, template, tmp_output_dir):
        paths = writer.write_all([doc], template, tmp_output_dir)
        html_content = paths[0].read_text(encoding="utf-8")
        assert "readonly" in html_content

    def test_html_escapes_special_chars(self, writer, template, tmp_output_dir):
        doc = ExtractedDocument(source_filename="test_xss.pdf", sections=[
            ExtractedSection(name="Header", fields={"Batch No": '<script>alert("xss")</script>'}),
        ])
        paths = writer.write_all([doc], template, tmp_output_dir)
        html_content = paths[0].read_text(encoding="utf-8")
        assert "<script>" not in html_content
        assert "&lt;script&gt;" in html_content

    def test_multiple_documents(self, writer, template, tmp_output_dir):
        docs = [
            ExtractedDocument(source_filename="a.pdf", sections=[]),
            ExtractedDocument(source_filename="b.pdf", sections=[]),
        ]
        paths = writer.write_all(docs, template, tmp_output_dir)
        assert len(paths) == 2
        assert {p.name for p in paths} == {"a.html", "b.html"}

    def test_contains_document_type(self, writer, doc, template, tmp_output_dir):
        paths = writer.write_all([doc], template, tmp_output_dir)
        html_content = paths[0].read_text(encoding="utf-8")
        assert "Certificate" in html_content
