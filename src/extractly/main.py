"""CLI entry point for Extractly.

Provides three commands:
  - scout:   Analyze a sample document to discover its structure
  - extract: Batch-extract data from a folder of documents
  - run:     Do both scout + extract in one go

Usage:
    python -m extractly scout --sample input_docs/sample.pdf
    python -m extractly extract --input-dir input_docs/
    python -m extractly run --sample input_docs/sample.pdf --input-dir input_docs/
"""

import logging
from pathlib import Path

import typer

from extractly.config import get_settings, setup_logging
from extractly.clients.gemini_client import GeminiClient
from extractly.models.template import MasterTemplate
from extractly.services.template_scout import TemplateScout
from extractly.services.batch_engine import BatchEngine
from extractly.services.excel_writer import ExcelWriter
from extractly.services.html_writer import HtmlWriter

app = typer.Typer(
    name="extractly",
    help="Gemini-powered document data extraction utility.",
    add_completion=False,
)

logger = logging.getLogger(__name__)


def _create_client() -> GeminiClient:
    """Create a GeminiClient from environment settings."""
    settings = get_settings()
    settings.validate_api_key()
    return GeminiClient(api_key=settings.gemini_api_key, model=settings.gemini_model)


@app.command()
def scout(
    sample: Path = typer.Option(..., help="Path to a sample PDF document."),
    output: Path = typer.Option(None, help="Path for the template JSON (default: output/master_template.json)."),
) -> None:
    """Task 1: Analyze a sample document to discover its structure."""
    settings = get_settings()
    setup_logging(settings.log_level)

    if output is None:
        output = settings.output_dir / "master_template.json"

    client = _create_client()
    template_scout = TemplateScout(client=client)

    typer.echo(f"🔍 Analyzing sample document: {sample}")
    template = template_scout.discover(sample)

    saved_path = template_scout.save_template(template, output)
    typer.echo(f"✅ Template saved to: {saved_path}")
    typer.echo(f"   Document type: {template.document_type}")
    typer.echo(f"   Sections found: {len(template.sections)}")

    for section in template.sections:
        typer.echo(f"   • {section.name} ({len(section.fields)} fields)")


@app.command()
def extract(
    input_dir: Path = typer.Option(None, help="Directory containing PDF documents."),
    template_path: Path = typer.Option(None, help="Path to master_template.json (default: output/master_template.json)."),
) -> None:
    """Tasks 2+3: Batch-extract data and generate Excel + HTML outputs."""
    settings = get_settings()
    setup_logging(settings.log_level)

    if input_dir is None:
        input_dir = settings.input_dir
    if template_path is None:
        template_path = settings.output_dir / "master_template.json"

    # Load the template
    if not template_path.exists():
        typer.echo(f"❌ Template not found: {template_path}")
        typer.echo("   Run 'extractly scout' first to create the template.")
        raise typer.Exit(code=1)

    template = MasterTemplate.model_validate_json(
        template_path.read_text(encoding="utf-8")
    )
    typer.echo(f"📋 Loaded template: {template.document_type}")

    # Run batch extraction
    client = _create_client()
    engine = BatchEngine(
        client=client,
        poll_interval=settings.batch_poll_interval_seconds,
        timeout=settings.batch_timeout_seconds,
    )

    typer.echo(f"⚡ Starting batch extraction from: {input_dir}")
    documents = engine.extract(input_dir, template, settings.output_dir)
    typer.echo(f"✅ Extracted data from {len(documents)} documents")

    # Generate Excel output
    excel_path = settings.output_dir / "master_output.xlsx"
    ExcelWriter().write(documents, template, excel_path)
    typer.echo(f"📊 Excel saved: {excel_path}")

    # Generate HTML outputs
    html_dir = settings.output_dir / "html"
    html_paths = HtmlWriter().write_all(documents, template, html_dir)
    typer.echo(f"🌐 HTML forms saved: {html_dir} ({len(html_paths)} files)")


@app.command()
def run(
    sample: Path = typer.Option(..., help="Path to a sample PDF document."),
    input_dir: Path = typer.Option(None, help="Directory containing PDF documents."),
) -> None:
    """Run the full pipeline: scout + extract + generate outputs."""
    settings = get_settings()
    setup_logging(settings.log_level)

    if input_dir is None:
        input_dir = settings.input_dir

    client = _create_client()

    # Task 1: Scout
    typer.echo("=" * 60)
    typer.echo("📝 TASK 1: Structural Discovery")
    typer.echo("=" * 60)

    template_scout = TemplateScout(client=client)
    template = template_scout.discover(sample)
    template_path = settings.output_dir / "master_template.json"
    template_scout.save_template(template, template_path)

    typer.echo(f"✅ Template: {template.document_type} ({len(template.sections)} sections)")

    # Task 2: Batch Extraction
    typer.echo("\n" + "=" * 60)
    typer.echo("⚡ TASK 2: Batch Extraction")
    typer.echo("=" * 60)

    engine = BatchEngine(
        client=client,
        poll_interval=settings.batch_poll_interval_seconds,
        timeout=settings.batch_timeout_seconds,
    )
    documents = engine.extract(input_dir, template, settings.output_dir)
    typer.echo(f"✅ Extracted: {len(documents)} documents")

    # Task 3: Output Generation
    typer.echo("\n" + "=" * 60)
    typer.echo("📊 TASK 3: Output Generation")
    typer.echo("=" * 60)

    excel_path = settings.output_dir / "master_output.xlsx"
    ExcelWriter().write(documents, template, excel_path)
    typer.echo(f"📊 Excel: {excel_path}")

    html_dir = settings.output_dir / "html"
    html_paths = HtmlWriter().write_all(documents, template, html_dir)
    typer.echo(f"🌐 HTML: {html_dir} ({len(html_paths)} files)")

    typer.echo("\n" + "=" * 60)
    typer.echo("🎉 Extractly pipeline complete!")
    typer.echo("=" * 60)
