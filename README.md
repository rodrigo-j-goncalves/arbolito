# Arbolito

Generates an interactive, animated mind map HTML file from a simple CSV spreadsheet.
The output is a self-contained HTML file suitable for embedding in Quarto RevealJS slides.

---

## Files

| File | Purpose |
|---|---|
| `arbolito.py` | Python script that reads the CSV and writes the HTML |
| `mindmap.csv` | Your content (edit this) |
| `mindmap.html` | Generated output (do not edit directly) |

---

## Requirements

Python 3.7+ with no extra dependencies (uses only the standard library).
An internet connection is required at viewing time to load D3.js and the Atkinson Hyperlegible font from CDN.

---

## Usage

```bash
python arbolito.py
```

This reads `mindmap.csv` and writes `mindmap.html` in the same directory.

### Options

```bash
python arbolito.py --input my_topic.csv --output my_topic.html

# Also save the intermediate JSON tree for inspection:
python arbolito.py --input my_topic.csv --output my_topic.html --save-json tree.json
```

---

## CSV Format

Open or create your CSV in any spreadsheet application (LibreOffice Calc, etc.) or a plain text editor.

### Columns

- `L1`, `L2`, `L3`, ... — Hierarchy levels. Add as many as needed. Each node belongs to the level column where its name is written; all other level columns on that row are left empty.
- `collapsed` — Whether the node starts collapsed. Write `false` to start expanded. Leave blank to use the default (collapsed).
- `fontSize` — Font size in pixels for this node's label. Leave blank to use the default (13px).

### Example — Ecology

```
L1,      L2,           L3,                          collapsed, fontSize
Ecology, ,             ,                            false,     15
,        Population,   ,                            true,
,        ,             Growth models,               ,
,        ,             Demography,                  ,
,        Communities,  ,                            true,
,        ,             Ecological interactions,     ,
,        ,             Abundance and distribution,  ,
,        Systems,      ,                            true,
```

This produces a tree like:

```
Ecology
├── Population
│   ├── Growth models
│   └── Demography
├── Communities
│   ├── Ecological interactions
│   └── Abundance and distribution
└── Systems
```

### Rules

- The root node must be in the `L1` column.
- A node at level `Ln` must appear after a node at level `L(n-1)` — you cannot skip levels.
- Blank rows are ignored.
- `collapsed: false` means the node's children are visible on load. Any other value or blank means collapsed.
- `fontSize` affects only the label of that specific node. Child nodes are not affected.

### Metadata (optional)

Rows before the header starting with `META` are displayed in a bar below the toolbar:

```
META, title,      My Topic
META, author,     Jane Smith
META, university, University of Example
META, date,       2026
L1, L2, collapsed, fontSize
...
```

---

## Interacting with the Mind Map

| Action | Effect |
|---|---|
| Click a node | Expand or collapse its children |
| Expand / collapse | Viewport auto-fits to show all visible nodes |
| Drag | Pan the view (disables auto-fit) |
| Scroll / pinch | Zoom in and out (disables auto-fit) |
| Change layout | Resets auto-fit and re-fits to the new layout |
| Layout buttons | Switch between Radial, Top-down, and Horizontal layouts |

---

## Embedding in Quarto RevealJS

Save `mindmap.html` next to your `.qmd` file, then insert a slide like this:

```markdown
## My Mind Map

<iframe src="mindmap.html" width="100%" height="600px" frameborder="0"></iframe>
```

You can adjust the `height` value to fit your slide dimensions.
