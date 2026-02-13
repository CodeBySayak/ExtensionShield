# Hero carousel static icons

Place PNG files here for **instant** hero orbital carousel load. Each file must be named by extension ID:

- `{extensionId}.png` — e.g. `session-buddy.png`, `ublock.png`, `grammarly.png`

The hero uses these URLs first (`/hero-icons/<id>.png`). If a file is missing, the app falls back to the API icon.

**Snapshot extension IDs** (from `frontend/src/data/heroSnapshot.js`):

session-buddy, hover-zoom, stylus, adblock, honey, grammarly, hola, vdh, ublock, lastpass, react-devtools, json-viewer, bitwarden, dark-reader, webde, tampermonkey, https-everywhere

Export icons from your scanned extensions (or Chrome Web Store) and save as the above filenames for sub-second hero render.
