import sys
from pathlib import Path

from docling.document_converter import DocumentConverter


def convert(pdf_path: str, output_dir: str = "data") -> Path:
    src = Path(pdf_path)
    if not src.exists():
        print(f"File not found: {src}")
        sys.exit(1)

    converter = DocumentConverter()
    result = converter.convert(str(src))
    markdown = result.document.export_to_markdown()

    out = Path(output_dir) / (src.stem + ".md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(markdown, encoding="utf-8")
    print(f"Saved: {out}")
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pdf_to_md.py <file.pdf> [output_dir]")
        print("       output_dir defaults to 'data/'")
        sys.exit(1)

    pdf = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "data"
    convert(pdf, out_dir)
