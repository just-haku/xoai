"""Document generation tools — native, no LLM tokens wasted."""


async def convert_to_docx(source_text: str, output_name: str, user_id: str) -> str:
    try:
        from docx import Document
    except ImportError:
        return "Error: 'python-docx' not installed. Run: pip install python-docx"

    from xoai.workspace.service import resolve_safe_path
    doc = Document()
    for para in source_text.split("\n"):
        doc.add_paragraph(para)

    safe_path = resolve_safe_path(user_id, output_name)
    doc.save(safe_path)
    return f"OK: {output_name}"


async def convert_to_pdf(source_text: str, output_name: str, user_id: str) -> str:
    # TODO: Implement with reportlab or weasyprint
    return "Error: PDF conversion not yet implemented."
