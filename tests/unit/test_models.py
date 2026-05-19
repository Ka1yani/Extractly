"""Tests for data models (template and extraction)."""

import json

import pytest

from extractly.models.template import Field, MasterTemplate, Section
from extractly.models.extraction import ExtractedDocument, ExtractedSection


# ---------------------------------------------------------------------------
# Field model tests
# ---------------------------------------------------------------------------
class TestField:
    """Tests for the Field model."""

    def test_create_field_with_label_and_type(self) -> None:
        """Field should store label and field_type."""
        field = Field(label="Batch Number", field_type="text")
        assert field.label == "Batch Number"
        assert field.field_type == "text"

    def test_field_default_type_is_text(self) -> None:
        """Field type should default to 'text' when not specified."""
        field = Field(label="Name")
        assert field.field_type == "text"

    def test_field_serialization(self) -> None:
        """Field should serialize to dict correctly."""
        field = Field(label="Date", field_type="date")
        data = field.model_dump()
        assert data == {"label": "Date", "field_type": "date"}

    def test_field_from_dict(self) -> None:
        """Field should deserialize from dict correctly."""
        field = Field.model_validate({"label": "Amount", "field_type": "number"})
        assert field.label == "Amount"
        assert field.field_type == "number"


# ---------------------------------------------------------------------------
# Section model tests
# ---------------------------------------------------------------------------
class TestSection:
    """Tests for the Section model."""

    def test_create_section_with_fields(self) -> None:
        """Section should hold a name and list of fields."""
        section = Section(
            name="Header",
            fields=[
                Field(label="Batch No", field_type="text"),
                Field(label="Date", field_type="date"),
            ],
        )
        assert section.name == "Header"
        assert len(section.fields) == 2

    def test_section_with_empty_fields(self) -> None:
        """Section should accept an empty field list."""
        section = Section(name="Footer", fields=[])
        assert section.fields == []

    def test_section_serialization_roundtrip(self) -> None:
        """Section should survive serialization and deserialization."""
        original = Section(
            name="Analysis",
            fields=[Field(label="pH", field_type="number")],
        )
        json_str = original.model_dump_json()
        restored = Section.model_validate_json(json_str)
        assert restored == original


# ---------------------------------------------------------------------------
# MasterTemplate model tests
# ---------------------------------------------------------------------------
class TestMasterTemplate:
    """Tests for the MasterTemplate model."""

    @pytest.fixture
    def sample_template(self) -> MasterTemplate:
        """Create a sample template for reuse across tests."""
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
                Section(
                    name="Analysis",
                    fields=[
                        Field(label="Assay", field_type="number"),
                        Field(label="pH", field_type="number"),
                    ],
                ),
            ],
        )

    def test_document_type(self, sample_template: MasterTemplate) -> None:
        """Template should store the document type."""
        assert sample_template.document_type == "Certificate of Analysis"

    def test_sections_count(self, sample_template: MasterTemplate) -> None:
        """Template should have the correct number of sections."""
        assert len(sample_template.sections) == 2

    def test_all_field_labels(self, sample_template: MasterTemplate) -> None:
        """all_field_labels should return flattened 'Section — Label' strings."""
        labels = sample_template.all_field_labels()
        assert labels == [
            "Header — Batch Number",
            "Header — Date",
            "Analysis — Assay",
            "Analysis — pH",
        ]

    def test_all_field_labels_empty_template(self) -> None:
        """all_field_labels should return empty list for template with no fields."""
        template = MasterTemplate(document_type="Empty", sections=[])
        assert template.all_field_labels() == []

    def test_json_roundtrip(self, sample_template: MasterTemplate) -> None:
        """Template should survive JSON serialization/deserialization."""
        json_str = sample_template.model_dump_json(indent=2)
        restored = MasterTemplate.model_validate_json(json_str)
        assert restored == sample_template

    def test_from_dict(self) -> None:
        """Template should be constructable from a raw dict (as Gemini returns)."""
        raw = {
            "document_type": "Invoice",
            "sections": [
                {
                    "name": "Details",
                    "fields": [{"label": "Total", "field_type": "number"}],
                }
            ],
        }
        template = MasterTemplate.model_validate(raw)
        assert template.document_type == "Invoice"
        assert template.sections[0].fields[0].label == "Total"


# ---------------------------------------------------------------------------
# ExtractedSection model tests
# ---------------------------------------------------------------------------
class TestExtractedSection:
    """Tests for the ExtractedSection model."""

    def test_create_extracted_section(self) -> None:
        """ExtractedSection should hold name and field values."""
        section = ExtractedSection(
            name="Header",
            fields={"Batch Number": "B-2024-001", "Date": "2024-03-15"},
        )
        assert section.name == "Header"
        assert section.fields["Batch Number"] == "B-2024-001"

    def test_empty_fields(self) -> None:
        """ExtractedSection should accept empty fields dict."""
        section = ExtractedSection(name="Footer", fields={})
        assert section.fields == {}


# ---------------------------------------------------------------------------
# ExtractedDocument model tests
# ---------------------------------------------------------------------------
class TestExtractedDocument:
    """Tests for the ExtractedDocument model."""

    @pytest.fixture
    def sample_doc(self) -> ExtractedDocument:
        """Create a sample extracted document for reuse."""
        return ExtractedDocument(
            source_filename="doc1.pdf",
            sections=[
                ExtractedSection(
                    name="Header",
                    fields={"Batch Number": "B-001", "Date": "2024-01-15"},
                ),
                ExtractedSection(
                    name="Analysis",
                    fields={"Assay": "99.2%", "pH": "7.4"},
                ),
            ],
        )

    def test_source_filename(self, sample_doc: ExtractedDocument) -> None:
        """Document should store the source filename."""
        assert sample_doc.source_filename == "doc1.pdf"

    def test_get_field_value_found(self, sample_doc: ExtractedDocument) -> None:
        """get_field_value should return the value when field exists."""
        assert sample_doc.get_field_value("Header", "Batch Number") == "B-001"
        assert sample_doc.get_field_value("Analysis", "pH") == "7.4"

    def test_get_field_value_missing_field(self, sample_doc: ExtractedDocument) -> None:
        """get_field_value should return empty string for missing field."""
        assert sample_doc.get_field_value("Header", "Nonexistent") == ""

    def test_get_field_value_missing_section(self, sample_doc: ExtractedDocument) -> None:
        """get_field_value should return empty string for missing section."""
        assert sample_doc.get_field_value("Nonexistent", "Batch Number") == ""

    def test_json_roundtrip(self, sample_doc: ExtractedDocument) -> None:
        """ExtractedDocument should survive JSON serialization/deserialization."""
        json_str = sample_doc.model_dump_json()
        restored = ExtractedDocument.model_validate_json(json_str)
        assert restored == sample_doc
