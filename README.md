# tesserae-widgets

Private widget catalog for [Tesserae](https://github.com/dmellok/tesserae).
`widgets.json` is the index a Tesserae server fetches; each entry pins a tagged
release tarball plus its sha256, and Settings → Widgets → Browse installs from
it.

This is a *parallel* catalog, not a fork of the community one. Widgets that are
generally useful belong in
[dmellok/tesserae-widgets](https://github.com/dmellok/tesserae-widgets) instead;
this index carries the ones that are specific to my setup, or not yet ready to
submit upstream.

## Pointing a server here

Settings → Server → App → **Marketplace catalog URL**:

```
https://raw.githubusercontent.com/TiagoJMartins/tesserae-widgets/main/widgets.json
```

Leave it at the default to use the community catalog instead; the setting takes
one URL, so a server browses one catalog at a time.

## Layout

```
widgets.json                    the index Tesserae fetches
schema/marketplace.schema.json  copy of the host's index schema (validate.py checks against it)
screenshots/<id>/lg.png         per-widget thumbnails (lg required, xs/sm/md optional)
scripts/validate.py             `mise run validate`: schema + sha256 + screenshot + folder layout
```

Validation is a local task, not CI: there is no GitHub Actions workflow here, so
`mise run validate` before a push is what keeps a bad pin out of Browse.

## Adding an entry

Each widget lives in its own repo and ships as a tagged release; this repo only
carries the index and the screenshots. The entry shape is
`schema/marketplace.schema.json`; the
[publishing guide](https://docs.tesserae.ink/dev/publishing-a-widget/) covers
the tarball/sha256 mechanics.

Bundles (a display widget plus its `_core` data plugin) ship as one entry with
`kind: "widget"` and a `folders` array naming every plugin directory in the
tarball; the catalog's `kind` enum has no `data`, so a data-only plugin cannot
be published on its own.

## Keeping the schema in sync

`schema/marketplace.schema.json` is a copy of the host's. When Tesserae bumps
its index schema, copy the new file in — `mise run validate` checks against the
local copy, so drift surfaces here before a user hits it on Browse.
