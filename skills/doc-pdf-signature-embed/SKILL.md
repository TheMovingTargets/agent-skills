---
name: doc-pdf-signature-embed
description: Embed one or more handwritten signature image files into PDF or Word `.docx` documents, either by interviewing the user to create a reusable placement configuration or by replaying a previously saved readable JSON config in batch mode. Use when a user provides PDF or Word files and signature image files and asks to sign, stamp, place, attach, embed, or batch-apply signatures to documents.
---

# DOC/PDF Signature Embed

Place signature images in PDF pages or Word documents with a reusable JSON configuration.

## Modes

- **Interactive mode**: interview the user, inspect PDFs as needed, create a config file, then apply it.
- **Batch mode**: validate and apply an existing config file without re-interviewing.

Always require at least one PDF or DOCX document and at least one signature image file before applying signatures. Do not imply legal advice, identity verification, or cryptographic/digital signing; this skill places visible signature images only.

## Helper Script

Use `scripts/pdf_signature_embed.py` for deterministic config creation, validation, and application.

```bash
python3 scripts/pdf_signature_embed.py init-config \
  --pdf contract.pdf \
  --signature signature.png \
  --output signature-config.json \
  --bundle-signatures \
  --instruction "Place signatures below printed names unless the user says otherwise."

python3 scripts/pdf_signature_embed.py validate \
  --config signature-config.json

python3 scripts/pdf_signature_embed.py apply \
  --config signature-config.json

python3 scripts/pdf_signature_embed.py bundle-signatures \
  --config signature-config.json \
  --signature-instruction primary="Use the cropped transparent version when available."
```

The script expects PyMuPDF for PDFs and `python-docx` for Word documents. If unavailable, install only the needed dependency in the active environment:

```bash
python3 -m pip install pymupdf
python3 -m pip install python-docx
```

Read `references/config-format.md` when creating or editing config files manually.

## Interactive Workflow

1. Confirm the input PDFs, signature images, and desired output directory or filename pattern.
2. Determine each placement:
   - target PDF;
   - target page, using 1-based page numbers for PDFs;
   - signature image;
   - for PDFs: anchor point, `x` and `y` coordinates in PDF points from the bottom-left page corner, and width/height;
   - for DOCX: insertion `mode` (`placeholder`, `after-paragraph`, or `append`), matching text if needed, image width in points, and optional paragraph `alignment` (`left`, `center`, or `right`).
3. If the user is unsure where to place the signature, render or inspect the target page with an available PDF tool and ask one focused question at a time. Prefer concrete choices such as "page 4, below the printed name line" and translate them into coordinates.
4. Generate a JSON config with `init-config`, then edit the `placements` array to match the interview.
5. If the user wants future replay, run `bundle-signatures` so the config carries local copies of signature files and any customization instructions next to the config.
6. Run `validate`, show the user a concise placement summary, and ask for confirmation before applying if any location was inferred.
7. Run `apply`.
8. If the harness can render PDFs or DOCX files, visually inspect the signed output. Otherwise report that validation was structural only.

## Batch Workflow

1. Run `validate --config <config.json>`.
2. If validation passes, run `apply --config <config.json>`.
3. Preserve the config file and any adjacent `<config-stem>-assets/` folder for replay. Treat relative paths in the config as relative to the config file location.

## Placement Rules

- Use PDF points: 72 points equals 1 inch.
- Store page numbers as 1-based integers in configs.
- Preserve original PDFs; write signed copies to configured output paths.
- For multiple signers or repeated signatures, add one placement object per visible signature.
- Keep config files free of secrets. They may contain document paths, output paths, coordinates, signer labels, signature image paths, and non-sensitive customization instructions.
- Prefer bundled signature paths for reusable configs: `bundle-signatures` copies signature images under `<config-stem>-assets/signatures/` and rewrites `signatures[].path` to a relative path.
- For Word documents, prefer an explicit placeholder such as `[[signature]]` when the template can be edited. Use `after-paragraph` only when the matching text is stable. Use `append` only when the user explicitly wants the signature at the end.
- If a PDF is encrypted, damaged, or requires a password, stop and ask for the needed password or a usable copy.
- If a DOCX is protected, corrupted, or cannot be opened, stop and ask for an editable copy.
