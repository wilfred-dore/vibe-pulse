---
name: canvas-to-cli
description: Give any Canvas deliverable a terminal twin. Use whenever the user asks for a document, brief, report, table, dashboard or chart (anything Vibe Work would put in a Canvas), or asks to run a Canvas-producing skill inside Vibe Code - produce the artifact as markdown/JSON/CSV files and render them in the terminal with vibe-plot.
---

# canvas-to-cli

Every Canvas artifact has a terminal twin. Map the deliverable to a renderer:

| Canvas artifact          | files to produce            | terminal rendering                  |
|--------------------------|-----------------------------|-------------------------------------|
| document / brief / report| `<name>.md`                 | `vibe-plot <name>.md --doc`         |
| data table               | CSV or JSONL                | `vibe-plot <file> --table`          |
| chart                    | CSV / JSONL                 | `vibe-plot <file>` (`--bar`, `--hist`, `--heatmap`, ...) or the `plot_metrics` tool |
| diagram                  | `.puml`                     | `vibe-plot <file> --diagram`        |
| slide-like summary       | several short `.md` pages   | sequence of `--doc` renders         |

## Workflow

1. Build the content from the user's data or task (analyze first, write second).
2. Write the artifacts under `runs/canvas/<slug>/`.
3. Render each artifact with the matching mode above, in a sensible order
   (document first, then tables, then charts).
4. Close by listing the produced files - they are plain markdown/CSV, ready to
   export to Notion, SharePoint or email exactly like a Work Canvas would be.

## Converting an existing Canvas skill

When asked to run a Work/Canvas skill inside the CLI: follow that skill's
instructions for the *content*, but replace every "create a Canvas" step with
the file + rendering mapping above. The deliverable is identical; the surface
is the terminal.
