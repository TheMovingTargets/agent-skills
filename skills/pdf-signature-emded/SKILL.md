---
name: pdf-signature-emded
description: Embed one or more handwritten signature image files into one or more PDF documents, either by interviewing the user to create a reusable placement configuration or by replaying a previously saved readable JSON config in batch mode. Use when a user provides PDF files and signature image files and asks to sign, stamp, place, attach, embed, or batch-apply signatures to PDFs.
---

# PDF Signature Emded

Place signature images on PDF pages with a reusable JSON configuration.

## Modes

- **Interactive mode**: interview the user, inspect PDFs as needed, create a config file, then apply it.
- **Batch mode**: validate and apply an existing config file without re-interviewing.

Always require at least one PDF document and at least one signature image file before applying signatures. Do not imply legal advice, identity verification, or cryptographic/digital signing; this skill places visible signature images only.

## Helper Script

Use `scripts/pdf_signature_embed.py` for deterministic config creation, validation, and application.

```bash
python3 scripts/pdf_signature_embed.py init-config \
  --pdf contract.pdf \
  --signature signature.png \
  --output signature-config.json

python3 scripts/pdf_signature_embed.py validate \
  --config signature-config.json

python3 scripts/pdf_signature_embed.py apply \
  --config signature-config.json
```

The script expects PyMuPDF. If unavailable, install it in the active environment:

```bash
python3 -m pip install pymupdf
```

Read `references/config-format.md` when creating or editing config files manually.

## Interactive Workflow

1. Confirm the input PDFs, signature images, and desired output directory or filename pattern.
2. Determine each placement:
   - target PDF;
   - target page, using 1-based page numbers;
   - signature image;
   - anchor point: `top-left`, `top-right`, `bottom-left`, `bottom-right`, or `center`;
   - `x` and `y` coordinates in PDF points measured from the bottom-left page corner;
   - width and height in PDF points, or width only with proportional height.
3. If the user is unsure where to place the signature, render or inspect the target page with an available PDF tool and ask one focused question at a time. Prefer concrete choices such as "page 4, below the printed name line" and translate them into coordinates.
4. Generate a JSON config with `init-config`, then edit the `placements` array to match the interview.
5. Run `validate`, show the user a concise placement summary, and ask for confirmation before applying if any location was inferred.
6. Run `apply`.
7. If the harness can render PDFs, visually inspect the signed output. Otherwise report that validation was structural only.

## Batch Workflow

1. Run `validate --config <config.json>`.
2. If validation passes, run `apply --config <config.json>`.
3. Preserve the config file for replay. Treat relative paths in the config as relative to the config file location.

## Placement Rules

- Use PDF points: 72 points equals 1 inch.
- Store page numbers as 1-based integers in configs.
- Preserve original PDFs; write signed copies to configured output paths.
- For multiple signers or repeated signatures, add one placement object per visible signature.
- Keep config files free of secrets. They may contain document paths, output paths, coordinates, and signer labels.
- If a PDF is encrypted, damaged, or requires a password, stop and ask for the needed password or a usable copy.
