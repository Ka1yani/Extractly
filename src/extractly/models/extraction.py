"""Extraction result models.

These models hold the data extracted from each document by the Batch Engine.
They mirror the MasterTemplate structure but contain actual values instead
of just field definitions.

Example ExtractedDocument JSON:
    {
        "source_filename": "doc1.pdf",
        "sections": [
            {
                "name": "Header",
                "fields": {"Batch Number": "B-2024-001", "Date": "2024-03-15"}
            }
        ]
    }
"""

from pydantic import BaseModel


class ExtractedSection(BaseModel):
    """Extracted data for one section of a document.

    Attributes:
        name: Section name matching the MasterTemplate section.
        fields: Mapping of field label to extracted value.
    """

    name: str
    fields: dict[str, str]


class ExtractedDocument(BaseModel):
    """All data extracted from a single document.

    Attributes:
        source_filename: Original filename of the processed document.
        sections: List of sections with their extracted field values.
    """

    source_filename: str
    sections: list[ExtractedSection]

    def get_field_value(self, section_name: str, field_label: str) -> str:
        """Look up a specific field value by section and label.

        Args:
            section_name: Name of the section to search.
            field_label: Label of the field to retrieve.

        Returns:
            The extracted value, or empty string if not found.
        """
        for section in self.sections:
            if section.name == section_name:
                return section.fields.get(field_label, "")
        return ""
