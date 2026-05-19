"""Master JSON Template models.

These models define the "shape" of a document — its sections and fields.
The TemplateSscout (Task 1) produces a MasterTemplate.
The BatchEngine (Task 2) consumes it to guide extraction.

Example MasterTemplate JSON:
    {
        "document_type": "Certificate of Analysis",
        "sections": [
            {
                "name": "Header",
                "fields": [
                    {"label": "Batch Number", "field_type": "text"},
                    {"label": "Date", "field_type": "date"}
                ]
            }
        ]
    }
"""

from pydantic import BaseModel


class Field(BaseModel):
    """A single data field found in a document section.

    Attributes:
        label: Human-readable field name (e.g., "Batch Number").
        field_type: Data type hint (text, number, date, table).
    """

    label: str
    field_type: str = "text"


class Section(BaseModel):
    """A logical group of fields within a document.

    Attributes:
        name: Section heading (e.g., "Header", "Shipping Information").
        fields: List of fields belonging to this section.
    """

    name: str
    fields: list[Field]


class MasterTemplate(BaseModel):
    """The complete structural map of a document type.

    This is the output of Task 1 (Template Scout) and the input
    to Task 2 (Batch Engine) and Task 3 (Output Generators).

    Attributes:
        document_type: What kind of document this is (e.g., "Certificate of Analysis").
        sections: Ordered list of sections found in the document.
    """

    document_type: str
    sections: list[Section]

    def all_field_labels(self) -> list[str]:
        """Return a flat list of all field labels across all sections.

        Useful for building Excel column headers.

        Returns:
            List of strings like ["Header — Batch Number", "Header — Date", ...].
        """
        labels: list[str] = []
        for section in self.sections:
            for field in section.fields:
                labels.append(f"{section.name} — {field.label}")
        return labels
