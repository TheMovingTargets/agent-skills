# PDF Signature Config Format

Use JSON so configs remain portable across harnesses and languages.

## Minimal Example

```json
{
  "version": 1,
  "documents": [
    {
      "id": "contract",
      "path": "contract.pdf",
      "output": "signed/contract-signed.pdf"
    }
  ],
  "signatures": [
    {
      "id": "primary",
      "path": "signature.png"
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
    }
  ]
}
```

## Fields

- `version`: config format version. Use `1`.
- `documents`: PDF inputs.
- `documents[].id`: unique portable identifier.
- `documents[].path`: path to the input PDF. Relative paths resolve from the config file directory.
- `documents[].output`: output PDF path. Relative paths resolve from the config file directory.
- `signatures`: signature image inputs.
- `signatures[].id`: unique portable identifier.
- `signatures[].path`: path to a PNG, JPEG, or other image format accepted by PyMuPDF.
- `placements`: visible signature placements.
- `placements[].document`: `documents[].id`.
- `placements[].signature`: `signatures[].id`.
- `placements[].page`: 1-based target page number.
- `placements[].anchor`: point on the signature rectangle placed at `x`, `y`. Allowed values are `top-left`, `top-right`, `bottom-left`, `bottom-right`, and `center`.
- `placements[].x`: x coordinate in PDF points from the bottom-left page corner.
- `placements[].y`: y coordinate in PDF points from the bottom-left page corner.
- `placements[].width`: target image width in PDF points.
- `placements[].height`: optional target image height in PDF points. If omitted, the helper preserves image aspect ratio.
- `placements[].rotation`: optional clockwise degrees. Use `0`, `90`, `180`, or `270`; defaults to `0`.
- `placements[].label`: optional human-readable note for summaries.

## Coordinate Notes

PDF pages use points. Letter paper is usually `612 x 792` points. The helper accepts bottom-left coordinates in the JSON config and converts them to PyMuPDF's top-left drawing coordinates internally.

When a user describes a location visually, render the page and map the requested spot into PDF points. Keep the final config numeric and deterministic.
