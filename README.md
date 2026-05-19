# Extractly

> Gemini-powered document data extraction utility.

Upload one sample document → Extractly learns the structure → Batch-extract data from hundreds of similar documents → Get an Excel spreadsheet + individual HTML mirror forms.

## Quick Start

### 1. Install

```bash
# Create a virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Install Extractly and dev dependencies
pip install -e ".[dev]"
```

### 2. Configure

Copy `.env.example` to `.env` and add your Gemini API key:

```bash
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=your-key-here
```

Get your API key from [Google AI Studio](https://aistudio.google.com/apikey).

### 3. Run

```bash
# Step 1: Discover document structure from a sample
python -m extractly scout --sample input_docs/Raloxifene_Master_Sample.pdf

# Step 2: Batch-extract from all documents + generate outputs
python -m extractly extract --input-dir input_docs/

# Or do everything in one go:
python -m extractly run --sample input_docs/Raloxifene_Master_Sample.pdf --input-dir input_docs/
```

### Outputs

| Output | Location | Description |
|--------|----------|-------------|
| Template | `output/master_template.json` | Document structure definition |
| Excel | `output/master_output.xlsx` | All extracted data in one spreadsheet |
| HTML Forms | `output/html/*.html` | One mirror form per document |

## How It Works

1. **Template Scout** (Task 1): Uploads a sample PDF to the Gemini Files API. Uses Gemini's vision to analyze the document's visual layout and identify sections, field labels, and data types. Saves a Master JSON Template.

2. **Batch Engine** (Task 2): Uploads all target PDFs to the Files API. Builds a JSONL file pairing each document URI with an extraction prompt. Submits to the Gemini Batch API for cost-effective async processing. Polls until complete.

3. **Output Generation** (Task 3): Converts raw AI responses into:
   - An Excel spreadsheet (one row per document, one column per field)
   - HTML mirror forms (fieldset-grouped, pre-filled readonly inputs)

## Development

```bash
# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=extractly --cov-report=term-missing --cov-branch

# Lint
ruff check src/ tests/
```

## Project Structure

```
src/extractly/
├── main.py              # CLI entry point (Typer)
├── config.py            # Settings via pydantic-settings
├── models/
│   ├── template.py      # MasterTemplate, Section, Field
│   └── extraction.py    # ExtractedDocument, ExtractedSection
├── clients/
│   └── gemini_client.py # Thin Gemini SDK wrapper
└── services/
    ├── template_scout.py # Task 1: structural discovery
    ├── batch_engine.py   # Task 2: batch extraction
    ├── excel_writer.py   # Task 3A: Excel output
    └── html_writer.py    # Task 3B: HTML mirror forms
```

## Tech Stack

- **Python 3.12+**
- **google-genai** — Gemini Files API + Batch API
- **Pydantic v2** — data validation and settings
- **openpyxl** — Excel generation
- **Typer** — CLI framework
- **pytest** — testing
