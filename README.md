# Arbolito

**See it live here**: [arbolito](https://rodrigo-j-goncalves.github.io/serve/arbolito/arbolito_mindmap.html)

- Generate an interactive, animated mind map from a simple CSV spreadsheet.
- The output is a self-contained HTML file suitable for embedding in Quarto RevealJS slides (or in any other HTML-based context).
- Presentation-ready: you can pre-define the behavior (what is shown, in which order)

---

<p align="center">
  <img src="assets/README/image-1.png" alt="alt text" width="70%">
</p>

---

## Files

| File | Purpose |
| --- | --- |
| `arbolito_mindmap.csv` | Your content (edit this) |
| `arbolito.py` | Python script that reads the CSV and writes the HTML |
| `arbolito_mindmap.html` | This is the output: your html mindmap|

---

## Requirements

Python 3.7+ with no extra dependencies (uses only the standard library).
An internet connection is required at viewing time to load D3.js and the Atkinson Hyperlegible font from CDN.

---

## Usage

```bash
python arbolito.py
```

This reads `arbolito_mindmap.csv` and writes `arbolito_mindmap.html` in the same directory.

### Options

#### Use your own filenames

- You can specify `input` and `output` files:

    ```bash
    python arbolito.py --input mindmap.csv --output mindmap.html
    ```

#### Define the initial view

- You can set the initial view when the page loads:

    ```bash
    python arbolito.py --layout radial --theme light --expand all
    ```

    | Flag | Values | Default | Effect |
    | --- | --- | --- | --- |
    | `--layout` | `radial`, `topdown`, `horizontal` | `horizontal` | Initial layout |
    | `--theme` | `light`, `dark` | `dark` | Initial theme |
    | `--expand` | `all`, `none`, `file` | `file` | `all`/`none` force every node open/closed on load; `file` respects each row's `collapsed` column |
    | `--bg` | any CSS color | *(theme default)* | Override the canvas background (e.g. `'#1a1a2e'`, `transparent`) |


#### Export as JSON

- You can also save the intermediate JSON tree for inspection:

    ```bash
    python arbolito.py --input mindmap.csv --output mindmap.html --save-json tree.json
    ```

---

## Prepare you contents: the CSV file

Open or create your CSV in any spreadsheet application (e.g. LibreOffice Calc, MS Excel, etc.) or a plain text editor.

### How to organize your CSV file

#### META Rows

- You can add `META` rows to include additional information (eg Title, Author, University/Company, Date, etc.).
- This information will be shown on the mindmap (top-left corner).
- `META` rows are optional, and there is no maximum (but it won't look nice if you add too much text!).


Here I show an example where I include a `title`, `author`, `company`, and `date`. These names are just for your CSV file, and are not shown on the mindmap (you can add any other!). The mindmap shows the values only (third column)

<p align="center">
  <img src="assets/README/image-3.png" alt="alt text" width="50%">
</p>

And it looks like this, on the top-left corner of the mindmap:

<p align="center">
  <img src="assets/README/image-4.png" alt="alt text" width="50%">
</p>


#### Columns - organization

- The columns are organized as 'Levels' (Lx). A level is a box (node).
- `L1` is the 'grandparent' or first level (in the simple example: 'Sports superstars'), `L2` is the 1st 'parent' (in the example: the name of the sport), `L3` is the 'child' (in the example: whether the player won a WC or not), etc.

<p align="center">
  <img src="assets/README/image-5.png" alt="alt text" width="60%">
</p>

- As you can see, `L1`, `L2`, `L3`, ... are hierarchy levels.
- **You can add as many `Lx` as needed**.
- Each `Lx` node belongs to the level column where its name is written; all other level columns on that row are left empty.


#### Columns - Visualization options

Three more columns define how the mindmap is shown:

- `collapsed` — Whether the node is **initially collapsed**. Write `false` to start expanded. Leave blank to use the default (collapsed).
- `fontSize` — Font size in pixels for this node's label. Leave blank to use the default (13px).
- `link` — A URL for this node. Adds a small link icon in the corner of the node; clicking it opens the URL in a new tab without expanding/collapsing the node. Leave blank for no link.
- `order` — A step number (1, 2, 3, ...) for stepping through nodes one at a time, e.g. during a lecture. See [Use this in a presentation](#use-this-in-a-presentation).

#### Multiline node labels

To split a node label across two or more lines, type `\n` (backslash + n) directly in the cell:

```
Exposición \n Plaza Profesorado Permanente Laboral
```

Alternatively, press **Ctrl+Enter** (LibreOffice) or **Alt+Enter** (Excel) to insert a real newline in the cell — both approaches produce the same result.

### A simple, full example

This CSV structure:

<p align="center">
  <img src="assets/README/image-6.png" alt="alt text" width="60%">
</p>

Produces a tree like this:

```text
    Sports superstars
      ├── Fútbol
      │   ├── Won a WC
      │   │   ├── Leo Messi
      │   │   ├── Pelé
      │   │   └── Maradona
      │   └── Did not win a WC
      │       ├── Cristiano Ronaldo
      │       ├── Paolo Maldini
      │       └── Johan Cruyff
      └── Basket
          ├── Won a WC
          │   ├── Shaquille O'Neal
          │   ├── Pau Gasol
          │   └── Kevin Durant
          └── Did not win a WC
              ├── Michael Jordan
              ├── LeBron James
              └── Luka Dončić

```

which results in this mindmap:

**Initial view**

<p align="center">
  <img src="assets/README/image-7.png" alt="alt text" width="60%">
</p>


**Fully expanded**

<p align="center">
  <img src="assets/README/image-8.png" alt="alt text" width="60%">
</p>


### **See it live here!**
- [This is the CSV file](https://rodrigo-j-goncalves.github.io/serve/arbolito/arbolito_mindmap_simpleExample.csv)
- [See the rendered mindmap](https://rodrigo-j-goncalves.github.io/serve/arbolito/arbolito_mindmap_simpleExample.html)

### Rules

- The root node must be in the `L1` column.
- A node at level `Ln` must appear after a node at level `L(n-1)` — you cannot skip levels.
- Blank rows are ignored.
- `collapsed` = false means the node's children are visible on load. Any other value or blank means collapsed.
- `fontSize` value affects only the label of that specific node. Child nodes are not affected.
- `link` value affects only that specific node. Child nodes are not affected.
- Node labels can span multiple lines: type `\n` in the cell, or use Ctrl+Enter (LibreOffice) / Alt+Enter (Excel) to insert a real newline.
- `order` value affects only that specific node; it does not force its ancestors open — see [Use this in a presentation](#use-this-in-a-presentation).

---

## Interacting with the Mind Map

| Action | Effect |
| --- | --- |
| Click a node | Expand or collapse its children |
| Click the link icon (if present) | Opens the node's `link` URL in a new tab |
| Expand / collapse | Viewport auto-fits to show all visible nodes |
| Drag | Pan the view (disables auto-fit) |
| Scroll / pinch | Zoom in and out (disables auto-fit) |
| Change layout | Resets auto-fit and re-fits to the new layout |
| Hover top strip | Reveals the toolbar (layout, theme, expand/collapse buttons) |

---

## Use this in a presentation

### Embedding in Quarto RevealJS (or on your website!)

Save `arbolito_mindmap.html` next to your `.qmd` file, then insert a slide like this:

```markdown
## My Mind Map

<iframe src="arbolito_mindmap.html" width="100%" height="600px" frameborder="0"></iframe>
```

You can adjust the `height` value to fit your slide dimensions.

To blend the mind map into your slide's background, generate it with `--bg transparent` and add `style="background: transparent"` to the iframe:

```bash
python arbolito.py --bg transparent
```

```markdown
<iframe src="arbolito_mindmap.html" width="100%" height="600px"
        frameborder="0" style="background: transparent;"></iframe>
```

#### Toolbar auto-hide

The toolbar (layout, theme, expand/collapse buttons) is hidden by default to keep the view clean during presentations. Hover over the thin strip at the top of the mind map to reveal it. The META information bar (title, author, etc.) is always visible.


### Auto 'animate'

For lectures, it's useful to build up the mind map one topic at a time — e.g. "here's where we are in the program today" — advancing with the same key/clicker press you already use to move slides.

Add an `order` column to your CSV and number the nodes you want to step through: `1`, `2`, `3`, ... A node with `order` set starts out however its own `collapsed` value says (normally collapsed); each step expands the next node in the sequence — exactly like clicking it by hand. `order` doesn't force its ancestors open, so make sure a node's parent is already visible (via `collapsed=false`, or an earlier step) by the time its turn comes.

Opened on its own, the generated HTML responds to the keys below, so you can preview the sequence without any extra setup:

| Keys | Action |
| --- | --- |
| `→`, `SPACE`, `N` | Reveal the next `order` step |
| `←`, `SHIFT+SPACE`, `P` | Go back one step |

The Reset button (or reloading the page) restarts the sequence from the beginning.

#### Example

- This mindmap has uses the `order` column ([see the CSV here](https://rodrigo-j-goncalves.github.io/serve/arbolito/arbolito_mindmap_sequence.csv))
- You can check [here the rendered mindmap](https://rodrigo-j-goncalves.github.io/serve/arbolito/arbolito_mindmap_sequence.html) (just press the -> arrow and you'll see the mindmap become alive as pre-defined in the `order` column)

### Driving it from Quarto RevealJS with `splice`

To advance the mind map with the *same* keypress or remote-clicker press that moves your lecture slides — with focus automatically handed back to your main deck once the sequence ends — embed it with [`splice`](https://github.com/rodrigo-j-goncalves/splice), a Quarto extension for chaining a secondary Reveal.js-driven presentation into your slides:

```markdown
{{< splice "arbolito_mindmap.html" >}}
```

The generated HTML exposes a small Reveal.js-compatible interface (`getTotalSlides`, `next`, `prev`, ...) purely for `splice` to call — nothing about using the mind map on its own changes. `splice` steps through the `order`ed nodes one per keypress, and once the last one has been shown, the next advance passes straight through to your main presentation instead.

## License & Credits

- MIT Rodrigo J. Gonçalves
- I _claudeveloped_ this :p (Claude Code, claude-sonnet-4-6)
