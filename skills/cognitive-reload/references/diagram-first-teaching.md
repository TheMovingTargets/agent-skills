# Diagram-First Teaching

Use a diagram before code whenever relationships, branching, state, or boundaries matter.

## Output policy

Prefer a locally rendered Kroki image over a raw Mermaid fence. A normal Markdown image works in chat clients that do not implement Mermaid rendering.

1. Locate the bundled `scripts/kroki_url.py`.
2. Create concise Mermaid source in memory or a temporary file outside the production repository.
3. Run the script with `--alt` and `--check`:

```bash
printf '%s\n' 'flowchart TD' '  A["Client"] --> B["API"]' '  B --> C["Store"]' \
  | python3 scripts/kroki_url.py --alt "System flow" --check
```

4. Place the returned Markdown image on its own line in the chat response, exactly as printed by the helper. The default output is a short cached local PNG URL such as `http://127.0.0.1:8991/<hash>.png`; do not replace it with the longer Kroki URL.
5. Follow it with a compact prose or table summary so the explanation remains usable if the client blocks images.

The helper automatically applies a neutral Mermaid theme with explicit connector and
arrowhead colors. This is required because Kroki PNGs can be transparent and Mermaid's
default dark links nearly disappear against dark chat backgrounds. Do not add a Mermaid
`init` directive unless a diagram needs custom styling; a caller-supplied directive takes
precedence and must provide contrasting `lineColor`, `.flowchart-link`, and `.marker` colors.

The configured Kroki endpoint is read from `COGNITIVE_RELOAD_KROKI_URL` or `${XDG_CONFIG_HOME:-~/.config}/cognitive-reload/config.json`. The standard installer uses port `8990` and persists both `kroki_port` and `kroki_url` when invoked with `--with-kroki`. Respect that saved endpoint; never assume port `8000`.

By default, the helper renders through Kroki, stores the resulting PNG under `${XDG_CACHE_HOME:-~/.cache}/cognitive-reload/diagrams/`, starts a loopback static asset server on `127.0.0.1:8991` or the next free port, checks the cached URL, and emits that short URL. This avoids long opaque Base64 paths in assistant responses. Use `--direct-kroki-url` only for debugging.

Kroki URLs must be generated only by the helper. Do not hand-build image URLs
or paste raw Mermaid into the `/mermaid/png/...` path. The encoded path segment
must be unpadded URL-safe Base64; it should not end with `=`. If the chat shows
`Error 400: Unable to decode the source. The source is not in valid Base64 scheme`,
the browser is still requesting a direct `/mermaid/png/...` URL that was malformed
or mangled before Kroki received it. This usually means the image link was
handwritten, copied incompletely, wrapped across lines, edited after generation,
or generated with `--direct-kroki-url`. Regenerate the image with
`scripts/kroki_url.py --check`, paste the complete short cached helper output
unchanged, and do not retry the same direct Kroki URL.

If `--check` fails, do not use a broken image. Briefly say that local rendering is unavailable and use a Mermaid fence plus a concise text fallback. Do not send private repository diagrams to a public renderer.

## Choose the diagram

| Need | Diagram |
|---|---|
| Runtime pieces and dependencies | Mermaid flowchart |
| Request or event order | Mermaid sequence diagram |
| Lifecycle | Mermaid state diagram |
| Stored entities and ownership | Mermaid ER diagram |
| Decision logic | Mermaid flowchart |

## Chat layout budget

Treat chat width as a hard constraint:

- Emit at most one image per turn.
- Use 4-6 nodes normally and never exceed 8 nodes in one flowchart.
- Use `LR` or `RL` only for 2-4 nodes. Use `TD` for longer journeys.
- Split a journey into two diagrams when a vertical version would still need more than 8 nodes.
- Limit node labels to four words and about 28 characters. Put detail in prose below.
- Limit sequence diagrams to four participants and one interaction phase.
- Never compensate for crowding with tiny labels, manual widths, or a wider image.
- Do not repeat every diagram node as a long numbered list. Explain only 2-3 boundaries or decisions that the picture does not make obvious.

The bundled helper enforces the main limits. It automatically changes horizontal
flowcharts with more than four declared nodes to `TD`, rejects flowcharts above eight
nodes, and rejects sequence diagrams above four declared participants. If it rejects a
diagram, simplify or split the concept; do not bypass the guard or paste raw Mermaid.

Encoded GET URLs should remain comfortably below common browser URL limits. Include only relationships supported by repository evidence.

## Concept before implementation

For every topic:

1. Name the concept in domain language.
2. Show where it sits in the repository-level map.
3. Show the rendered flow or boundary without filenames.
4. Confirm the learner understands the concept.
5. Then map diagram nodes to files/functions.

Example mapping table:

| Concept | Implementation anchor |
|---|---|
| Authenticate device | `auth.py:require_agent` |
| Bind tenant identity | `events.py:_scope_agent_event` |
| Validate payload | `schemas.py:UsageEventIn` |
| Persist normalized event | `ingestion.py:ingest_event` |

## Avoid

- public rendering services for private repository information
- diagrams that merely restate a two-item sentence
- long left-to-right process chains that become unreadable at chat width
- a diagram followed by prose that enumerates every box again
- huge architecture maps before the learner knows the vocabulary
- filenames as the only labels in a conceptual diagram
- code before the diagram unless the learner explicitly requests code first
- claiming success merely because Kroki returned an image; the chat client smoke test must also pass

When a learner is confused, redraw the smallest relevant relationship instead of adding more prose.
