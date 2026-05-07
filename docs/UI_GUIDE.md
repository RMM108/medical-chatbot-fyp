# UI Guide

Notes for contributors working on the Medical Training Chatbot UI.

## Stack

- [Chainlit](https://docs.chainlit.io) 2.11+ — chat-UI framework. The
  React frontend is shipped with the package; we customize via config,
  CSS, and JS hooks rather than forking the frontend.
- [Plotly](https://plotly.com/python/) — embedded charts on the progress
  dashboard.

## Where UI Lives

| Surface                  | File                                               |
| ------------------------ | -------------------------------------------------- |
| Login screen welcome     | [`chainlit.md`](../chainlit.md)                    |
| Theme, title, header     | [`.chainlit/config.toml`](../.chainlit/config.toml) |
| All chat / button flows  | [`app.py`](../app.py)                              |
| Progress charts          | [`visualizations.py`](../visualizations.py)        |
| Static assets (CSS / JS) | `public/` — `tokens.css`, `theme.json`, `custom.css`, `medical-glyph.svg` |

## Running Locally for UI Work

```bash
chainlit run app.py -w
```

`-w` watches Python files for changes and reloads. CSS/JS edits in
`public/` need a manual browser refresh (no HMR).

### No RAG server needed

`RAGClient.check_connection()` returns `False` on any failure and the
app shows a "RAG server not connected" warning banner. Interviews
continue without retrieved context — perfect for local UI development.

If you want to silence the warning, leave `SERVER_URL` unset; the
default of `http://localhost:8000` will fail fast.

## Design System

The app follows a paper-white, pill-geometry design system inspired by
the Ollama documentation site. Three files in `public/` carry it:

| File                          | Role                                                              |
| ----------------------------- | ----------------------------------------------------------------- |
| `public/theme.json`           | shadcn/ui CSS variables (HSL) for `light` and `dark` modes        |
| `public/tokens.css`           | Source-of-truth design tokens (colors, fonts, radii, spacing)     |
| `public/custom.css`           | Selector overrides shadcn variables can't express (pill radius on buttons, 720px reading column, hairline cards, inverted dark surface for `[data-author="Evaluation"]`) |
| `public/medical-glyph.svg`    | The single line illustration used as logo + default avatar        |

The canonical design spec is a `DESIGN.md` file kept locally
(gitignored). It uses the [`@google/design.md`](https://github.com/google-labs-code/design.md)
format. `public/tokens.css` mirrors the spec by hand — when you change
the design language, update both together. Run
`npx @google/design.md lint DESIGN.md` to catch broken refs and WCAG
issues.

### Where the dark-card moment lives

DESIGN.md reserves exactly one inverted dark surface per page as the
"look here" cue. We bind it to messages with `author="Evaluation"`:

```python
await cl.Message(content=report, author="Evaluation").send()
```

`custom.css` then targets `[data-author="Evaluation"]` to render that
message on `--md-surface-dark`. Don't reuse this author label for
non-attention-grabbing content.

### Adding a new color or typography token

1. Add it to `DESIGN.md` (your local copy) — both the YAML front matter
   and the prose section that describes it.
2. Add the same variable to `public/tokens.css`.
3. If it's a global theme color, also map it in `public/theme.json` to
   the appropriate shadcn variable (`--background`, `--primary`, etc.).
4. If it's a one-off, reference the `--md-*` variable from `tokens.css`
   directly inside `custom.css`.

## Theme & Branding

`.chainlit/config.toml` highlights:

```toml
[UI]
name = "Medical Training Chatbot"
default_theme = "light"           # "dark" | "light"
# layout = "wide"
# default_sidebar_state = "open"
custom_css = "/public/custom.css"
# custom_js = "/public/app.js"
logo_file_url = "/public/medical-glyph.svg"
default_avatar_file_url = "/public/medical-glyph.svg"
# login_page_image = "/public/login-bg.jpg"
```

### Custom CSS

1. Create `public/style.css`.
2. In `config.toml`, set `custom_css = "/public/style.css"`.
3. Restart Chainlit (CSS is loaded at boot; not hot-reloaded).

Chainlit ships a class-naming convention; inspect with browser devtools
to find the right selectors. Common targets:
`.message`, `.chat-input`, `.action-button`, `.message-author`.

### Custom JavaScript

Same pattern: drop a file in `public/`, point `custom_js` at it.
Useful for analytics, custom keybindings, or DOM tweaks Chainlit doesn't
expose via config.

## Action Buttons

All chat actions are `cl.Action` objects attached to messages. Pattern
in [`app.py`](../app.py):

```python
actions = [
    cl.Action(
        name="end_session",                # callback name
        value="end",                       # legacy field
        payload={"action": "end_session"}, # passed to the callback
        label="📊 End Session & Evaluate", # button label
    ),
    # ...
]
await cl.Message(content="…", actions=actions, author="System").send()
```

Each `name` must have a matching `@cl.action_callback("name")` handler.
After handling, call `await action.remove()` to hide the button.

## Modes vs Buttons

`@cl.on_message` (the catch-all message handler) currently switches on
two boolean session flags:

- `analyze_mode` — student typed an exchange number to analyze
  ([`app.py:293`](../app.py:293))
- `history_mode` — student typed a session number to view
  ([`app.py:415`](../app.py:415))

If you add a similar "type a number to pick" interaction, prefer
generating buttons (see `analyze_mode` action callback at
[`app.py:977`](../app.py:977)) — fewer surprises and no need to clear
mode flags everywhere.

## Plotly Charts

Charts are constructed in [`visualizations.py`](../visualizations.py)
and embedded as `cl.Plotly` elements:

```python
elements = [
    cl.Plotly(name="progress_timeline", figure=fig, display="inline"),
]
await cl.Message(content="", elements=elements, author="Charts").send()
```

`display="inline"` renders inside the chat. Use `"side"` to open the
chart in the right panel. Color palette lives in
`ProgressVisualizer.colors`.

## Things That Are Awkward Today

| Pain point                                         | Where                                    |
| -------------------------------------------------- | ---------------------------------------- |
| Registration via pipe-delimited username string    | [`app.py:27`](../app.py:27)              |
| Up to 28 buttons for PHQ-9 score selection         | [`app.py:689`](../app.py:689)            |
| History/analyze require typing numbers             | [`app.py:415`](../app.py:415), [`app.py:293`](../app.py:293) |
| Long markdown blob for evaluation report           | [`app.py:1372`](../app.py:1372)          |
| `app.py` is one giant file                         | [`app.py`](../app.py)                    |

These are the highest-leverage targets if you're polishing the UI.

## Style Guide

- Match existing emoji usage in headings (`📊`, `📈`, `🩺`, `👤`) — the
  app's voice already leans on them.
- Use `author=` to label who's "speaking" (`"System"`, `"Stats"`,
  `"PHQ-9 Guide"`, `"Evaluation"`, the patient's name). It controls the
  avatar and label.
- Markdown headings render at full size; prefer `##` and `###` over `#`
  inside chat bubbles.
- Tables work — they're used heavily in the PHQ-9 briefing.

## Quick Wins to Try

1. Replace the score grid with a single message + slider (Chainlit
   supports `cl.Slider` via `chat_settings`, or roll a number input).
2. Add a `public/style.css` with brand colors and tighter spacing.
3. Set `logo_file_url` in `config.toml` so the header isn't blank.
4. Add a `login_page_image` for first impressions.
5. Move long evaluation reports into a side-panel
   `cl.Plotly`/`cl.Text` element instead of stuffing the chat.
