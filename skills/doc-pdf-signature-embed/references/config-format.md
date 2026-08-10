# PDF Signature Config Format

Use JSON so configs remain portable across harnesses and languages.

## Minimal Example

```json
{
  "version": 1,
  "customization_instructions": [
    "Place signatures below printed names unless the user says otherwise."
  ],
  "documents": [
    {
      "id": "contract",
      "type": "pdf",
      "path": "contract.pdf",
      "output": "signed/contract-signed.pdf"
    },
    {
      "id": "agreement",
      "type": "docx",
      "path": "agreement.docx",
      "output": "signed/agreement-signed.docx"
    }
  ],
  "signatures": [
    {
      "id": "primary",
      "path": "signature-config-assets/signatures/primary.png",
      "customization_instructions": [
        "Use the cropped transparent version when available."
      ]
    }
  ],
  "placements": [
    {
      "document": "contract",
      "signature": "primary",
      "page": 4,
      "anchor": "bottom-left",
      "x": 324,
      "y": 142,
      "width": 156
    },
    {
      "document": "agreement",
      "signature": "primary",
      "mode": "placeholder",
      "placeholder": "[[signature]]",
      "width": 120
    }
  ]
}
```

## Fields

- `version`: config format version. Use `1`.
- `customization_instructions`: optional array of non-sensitive notes collected during the interview. Use this for reusable placement preferences, output naming conventions, and visual QA expectations.
- `documents`: PDF inputs.
- `documents[].id`: unique portable identifier.
- `documents[].type`: optional when the extension is `.pdf` or `.docx`; otherwise use `pdf` or `docx`.
- `documents[].path`: path to the input PDF. Relative paths resolve from the config file directory.
- `documents[].output`: output document path. Relative paths resolve from the config file directory.
- `signatures`: signature image inputs.
- `signatures[].id`: unique portable identifier.
- `signatures[].path`: path to a PNG, JPEG, or other image format accepted by PyMuPDF.
- `signatures[].customization_instructions`: optional array of non-sensitive notes specific to that signer or signature image, such as "use cropped image" or "make no wider than 90 points".
- `placements`: visible signature placements.
- `placements[].document`: `documents[].id`.
- `placements[].signature`: `signatures[].id`.
- `placements[].page`: 1-based target page number. Required for PDFs.
- `placements[].anchor`: PDF-only point on the signature rectangle placed at `x`, `y`. Allowed values are `top-left`, `top-right`, `bottom-left`, `bottom-right`, and `center`.
- `placements[].x`: PDF-only x coordinate in PDF points from the bottom-left page corner.
- `placements[].y`: PDF-only y coordinate in PDF points from the bottom-left page corner.
- `placements[].width`: target image width in PDF points.
- `placements[].height`: optional target image height in PDF points. If omitted, the helper preserves image aspect ratio. Ignored for DOCX.
- `placements[].rotation`: optional PDF-only clockwise degrees. Use `0`, `90`, `180`, or `270`; defaults to `0`.
- `placements[].label`: optional human-readable note for summaries.
- `placements[].mode`: DOCX-only insertion mode. Use `placeholder`, `after-paragraph`, or `append`.
- `placements[].placeholder`: DOCX-only text token to replace with the inline signature image when `mode` is `placeholder`.
- `placements[].paragraph`: DOCX-only paragraph text fragment after which to insert the signature image when `mode` is `after-paragraph`.
- `placements[].alignment`: DOCX-only image paragraph alignment. Use `left`, `center`, or `right`; omitted placements preserve the Word default.

## Coordinate Notes

PDF pages use points. Letter paper is usually `612 x 792` points. The helper accepts bottom-left coordinates in the JSON config and converts them to PyMuPDF's top-left drawing coordinates internally.

When a user describes a location visually, render the page and map the requested spot into PDF points. Keep the final config numeric and deterministic.

For DOCX documents, avoid page coordinates. Word layout can reflow by renderer, fonts, and page setup. Prefer a placeholder token such as `[[signature]]`, or use a stable paragraph text fragment. Render the signed DOCX before delivery whenever possible.

## Bundled Signature Assets

For reusable configs, keep signature images next to the config instead of pointing at arbitrary files elsewhere on the machine:

```bash
python3 scripts/pdf_signature_embed.py bundle-signatures \
  --config signature-config.json \
  --instruction "Place signatures below printed names." \
  --signature-instruction primary="Use width 100 for this invoice template."
```

By default, the helper copies images to `<config-stem>-assets/signatures/` and rewrites `signatures[].path` as a relative path. Move or back up the config and its assets folder together.
