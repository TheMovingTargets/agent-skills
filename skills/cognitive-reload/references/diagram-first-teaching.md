# Diagram-First Teaching

Use a diagram before code whenever relationships, branching, state, or boundaries matter.

## Output policy

Always generate diagrams with the bundled `scripts/kroki_url.py` helper and paste its output
exactly. The helper has three render modes and chooses safely by default; you do not pick the
client's capabilities, you pick the mode.

1. Locate the bundled `scripts/kroki_url.py`.
2. Create concise Mermaid source in memory or a temporary file outside the production repository.
3. Run the helper (default `--render-mode auto`):

```bash
printf '%s\n' 'flowchart TD' '  A["Client"] --> B["API"]' '  B --> C["Store"]' \
  | python3 scripts/kroki_url.py --alt "System flow"
```

4. Place the helper output on its own line in the chat response, exactly as printed. Follow it with a
   compact prose or table summary so the explanation stays usable even if the client cannot render
   the diagram.

### Render modes

- **`fence` (default via `auto`).** Emits a native ```mermaid block. Zero dependencies, no network,
  and renders in GitHub, IDEs, and most agent UIs. This is the sanctioned default; a raw Mermaid
  fence from the helper is correct output, not a fallback.
- **`local`.** Renders a PNG through a self-hosted Kroki and serves it from a loopback cache
  (`127.0.0.1:8991`). `auto` selects this automatically only when a local renderer is explicitly
  configured (the `--with-kroki` installer records `render_mode: local`). Use this for private repos.
- **`public`.** Renders through `https://kroki.io`. **Opt-in only**: it sends the diagram source to a
  third party, so reach it only with explicit consent for a non-sensitive repository, via
  `--render-mode public` (or `COGNITIVE_RELOAD_RENDER_MODE=public`). A custom `--endpoint` alone does
  not enable egress. A public render URL embeds the diagram source (reversibly encoded), so it can
  also leak into shell history and logs.

In `auto`, if a configured local renderer is unreachable the helper degrades to a fence on its own;
a *layout-policy* rejection (too many nodes) is not degraded — simplify the diagram instead.

### Image-mode details (local and public)

For rendered images the helper applies a neutral Mermaid theme with explicit connector and
arrowhead colors, because Kroki PNGs can be transparent and Mermaid's default dark links nearly
disappear against dark chat backgrounds. Fence mode emits plain Mermaid with no `init` directive so
it does not fight the host UI theme. Do not add a Mermaid `init` directive unless a diagram needs
custom styling; a caller-supplied directive takes precedence and must provide contrasting
`lineColor`, `.flowchart-link`, and `.marker` colors.

The local Kroki endpoint is read from `COGNITIVE_RELOAD_KROKI_URL` or
`${XDG_CONFIG_HOME:-~/.config}/cognitive-reload/config.json`. The `--with-kroki` installer uses port
`8990` and persists `kroki_port`, `kroki_url`, and `render_mode: local`. Respect that saved
endpoint; never assume port `8000`. In `local` mode the helper stores the PNG under
`${XDG_CACHE_HOME:-~/.cache}/cognitive-reload/diagrams/`, starts a loopback asset server on
`127.0.0.1:8991` or the next free port, checks the cached URL, and emits that short URL. The
loopback URL only works when the renderer and the display UI share a host; remote or cloud harnesses
cannot reach it and should use `fence` (or `public` with consent). Use `--direct-kroki-url` only for
debugging.

Image URLs must be generated only by the helper. Do not hand-build image URLs or paste raw Mermaid
into a `/mermaid/png/...` path. The encoded path segment must be unpadded URL-safe Base64; it should
not end with `=`. If the chat shows `Error 400: Unable to decode the source. The source is not in
valid Base64 scheme`, a direct `/mermaid/png/...` URL was malformed or mangled before Kroki received
it — usually because the image link was handwritten, copied incompletely, wrapped across lines,
edited after generation, or generated with `--direct-kroki-url`. Regenerate with the helper, paste
the complete output unchanged, and do not retry the same direct URL.

If an image render fails, do not use a broken image: emit a Mermaid fence plus a concise text
fallback. Never send private repository diagrams to a public renderer.

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

The bundled helper enforces the main limits in every render mode. It automatically changes
horizontal flowcharts with more than four declared nodes to `TD`, rejects flowcharts above eight
nodes, and rejects sequence diagrams above four declared participants. If it rejects a diagram,
simplify or split the concept; do not bypass the guard. (A ```mermaid fence is acceptable only when
it is the helper's own output — never hand-paste raw Mermaid to dodge the guard.)

Encoded GET URLs (image modes) should remain comfortably below common browser URL limits. Include only relationships supported by repository evidence.

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
- sending diagram source to a public renderer without explicit consent for a non-sensitive repo
- in image modes, claiming success merely because Kroki returned an image; confirm it displays in the client

When a learner is confused, redraw the smallest relevant relationship instead of adding more prose.
