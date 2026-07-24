#!/usr/bin/env python3

"""
convert_docs.py

Recursively convert .docx files into Markdown.

Example:

python convert_docs.py \
    --input docs-word \
    --output docs
"""

from pathlib import Path
import argparse
import mammoth


# ------------------------------------------------------------
# Convert one DOCX
# ------------------------------------------------------------

def convert_docx(src: Path, dst: Path):

    dst.parent.mkdir(parents=True, exist_ok=True)

    with open(src, "rb") as docx_file:
        result = mammoth.convert_to_markdown(docx_file)

    markdown = result.value

    dst.write_text(markdown, encoding="utf-8")

    if result.messages:
        print(f"[WARN] {src}")
        for msg in result.messages:
            print(f"       {msg.message}")


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        required=True,
        help="Input DOCX directory",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Output Markdown directory",
    )

    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)

    if not input_dir.exists():
        raise FileNotFoundError(input_dir)

    count = 0

    for docx in input_dir.rglob("*.docx"):

        rel = docx.relative_to(input_dir)

        md = output_dir / rel.with_suffix(".md")

        print(f"{docx} -> {md}")

        convert_docx(docx, md)

        count += 1

    print()
    print(f"Converted {count} document(s).")


if __name__ == "__main__":
    main()
