convert_docs.py      # Recursive driver
    ├── converter.py         # Mammoth wrapper
    ├── cleaner.py           # Markdown cleanup
    ├── frontmatter.py       # YAML metadata
    ├── config.yaml
    └── requirements.txt

tools/
└── doc_converter/
    ├── README.md
    ├── requirements.txt
    ├── config.yaml
    ├── convert_docs.py          # Main entry point
    ├── converter.py             # DOCX → Markdown conversion
    ├── cleaner.py               # Markdown normalization
    ├── frontmatter.py           # YAML front matter
    ├── images.py                # Image extraction & path updates
    ├── links.py                 # Internal document link conversion
    ├── incremental.py           # Skip unchanged files
    ├── logger.py                # Console logging
    ├── utils.py                 # Common helpers
    ├── validators.py            # Markdown validation
    └── templates/
        └── frontmatter.yaml


python convert_docs.py \
    --input docs-word \
    --output docs
