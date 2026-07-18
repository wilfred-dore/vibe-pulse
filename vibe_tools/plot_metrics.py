"""Native Mistral Vibe tool: render charts directly in the conversation.

Loaded by Vibe's ToolManager via `tool_paths` in ~/.vibe/config.toml — the
same discovery mechanism as the builtin tools. Rendering is delegated to the
vibe-pulse `vibe-plot` CLI that lives next to this file, so the only runtime
requirement inside Vibe's environment is `uv` on PATH.
"""

from __future__ import annotations

import asyncio
import os
import re
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from vibe.core.tools.base import (
    BaseTool,
    BaseToolConfig,
    BaseToolState,
    InvokeContext,
    ToolError,
    ToolPermission,
)
from vibe.core.tools.ui import ToolCallDisplay, ToolResultDisplay, ToolUIData
from vibe.core.types import ToolStreamEvent

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


class PlotMetricsArgs(BaseModel):
    source: str = Field(
        description=(
            "File to visualize. line: JSONL metrics stream or CSV. "
            "heatmap: JSON {'labels': [...], 'matrix': [[...]]}. "
            "report: JSON {'classes': [...], 'precision': [...], 'recall': [...]}."
        )
    )
    kind: Literal["line", "scatter", "hist", "bar", "heatmap", "report", "compare"] = Field(
        default="line",
        description=(
            "Chart type: 'line' curves, 'scatter' points, 'hist' distribution "
            "of one column, 'bar' categories (x=labels, y=values), "
            "'heatmap' matrix, 'report' precision/recall bars, 'compare' one "
            "metric overlaid across several runs (source = comma-separated files)"
        ),
    )
    x: str | None = Field(default=None, description="x-axis key (line only; default: first numeric key)")
    y: str | None = Field(default=None, description="comma-separated series keys (line only; default: all numeric)")
    title: str | None = Field(default=None, description="Chart title")
    width: int = Field(default=60, description="Chart width in columns (line only)")
    height: int = Field(default=12, description="Chart height in rows (line only)")


class PlotMetricsResult(BaseModel):
    chart: str = Field(description="The rendered chart (Unicode/braille), already shown to the user")
    source: str
    kind: str
    # Colored variant consumed by the TUI widget below; excluded from
    # serialization so the model never pays tokens for escape codes.
    chart_ansi: str = Field(default="", exclude=True)


class PlotMetricsConfig(BaseToolConfig):
    permission: ToolPermission = ToolPermission.ALWAYS  # read-only rendering
    timeout: int = 30


class PlotMetricsState(BaseToolState):
    pass


class PlotMetrics(
    BaseTool[PlotMetricsArgs, PlotMetricsResult, PlotMetricsConfig, PlotMetricsState],
    ToolUIData[PlotMetricsArgs, PlotMetricsResult],
):
    description = (
        "Render a chart in the terminal from a data file: live-training metrics "
        "or any tabular data as braille line curves, a confusion matrix as a "
        "heatmap, or per-class precision/recall bars."
    )

    @classmethod
    def format_call_display(cls, args: PlotMetricsArgs) -> ToolCallDisplay:
        return ToolCallDisplay(summary=f"Plotting {args.kind}: {args.source}")

    @classmethod
    def format_result_display(cls, result: PlotMetricsResult) -> ToolResultDisplay:
        return ToolResultDisplay(
            success=True,
            message=f"{result.kind} chart from {Path(result.source).name}",
        )

    @classmethod
    def get_status_text(cls) -> str:
        return "Rendering chart"

    async def run(
        self, args: PlotMetricsArgs, ctx: InvokeContext | None = None
    ) -> AsyncGenerator[ToolStreamEvent | PlotMetricsResult, None]:
        def resolve(p: str) -> Path:
            path = Path(p.strip()).expanduser()
            if not path.is_absolute():
                path = Path.cwd() / path
            if not path.is_file():
                raise ToolError(f"source file not found: {path}")
            return path

        if args.kind == "compare":
            paths = [str(resolve(p)) for p in args.source.split(",")]
            if len(paths) < 2:
                raise ToolError("kind='compare' needs >= 2 comma-separated files")
            cmd = ["uv", "run", "--project", str(PROJECT_ROOT), "vibe-plot",
                   *paths, "--compare", "--width", str(args.width),
                   "--height", str(args.height)]
            if args.y:
                cmd += ["--y", args.y]
            source = Path(paths[0])
        else:
            source = resolve(args.source)
            cmd = ["uv", "run", "--project", str(PROJECT_ROOT), "vibe-plot", str(source)]
        if args.kind == "heatmap":
            cmd.append("--heatmap")
        elif args.kind == "report":
            cmd.append("--report")
        elif args.kind == "bar":
            if not (args.x and args.y):
                raise ToolError("kind='bar' needs x (category column) and y (value column)")
            cmd += ["--bar", "--x", args.x, "--y", args.y, "--width", str(args.width)]
        elif args.kind == "hist":
            column = args.y or args.x
            if not column:
                raise ToolError("kind='hist' needs the column name in 'y'")
            cmd += ["--hist", column, "--width", str(args.width)]
        elif args.kind != "compare":
            cmd += ["--width", str(args.width), "--height", str(args.height)]
            if args.kind == "scatter":
                cmd.append("--scatter")
            if args.x:
                cmd += ["--x", args.x]
            if args.y:
                cmd += ["--y", args.y]
        if args.title:
            cmd += ["--title", args.title]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(PROJECT_ROOT),
            env={**os.environ, "FORCE_COLOR": "1"},
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.config.timeout
            )
        except TimeoutError as err:
            proc.kill()
            raise ToolError(f"vibe-plot timed out after {self.config.timeout}s") from err

        if proc.returncode != 0:
            raise ToolError(
                f"vibe-plot failed ({proc.returncode}): "
                f"{stderr.decode(errors='replace').strip()[:500]}"
            )

        raw = stdout.decode(errors="replace").rstrip()
        chart = ANSI_RE.sub("", raw)
        if not chart:
            raise ToolError("vibe-plot produced no output")

        yield PlotMetricsResult(
            chart=chart, chart_ansi=raw, source=str(source), kind=args.kind
        )


try:
    # TUI-only enhancement: render the chart in full color inside the
    # conversation. Registering into RESULT_WIDGETS mirrors how builtins map
    # to their result widgets; harmless in headless (-p / ACP) contexts.
    from rich.text import Text
    from textual.app import ComposeResult
    from textual.widgets import Static
    from vibe.cli.textual_ui.widgets.tool_widgets import (
        RESULT_WIDGETS,
        ToolResultWidget,
    )

    class PlotMetricsResultWidget(ToolResultWidget):
        def compose(self) -> ComposeResult:
            if self.result is None:
                return
            ansi = getattr(self.result, "chart_ansi", "") or getattr(self.result, "chart", "")
            yield Static(Text.from_ansi(ansi), classes="tool-result-detail")

    RESULT_WIDGETS["plot_metrics"] = PlotMetricsResultWidget
except Exception:  # pragma: no cover - keep the tool usable without the TUI
    pass
