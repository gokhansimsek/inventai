"""Plotly charts for the HTML report.

Every chart shows a single series, so it carries one color and no legend: the
chart title names what is plotted. Different measures (revenue, margin %) get
separate charts rather than a second axis. Values and axes use text colors,
never the series color; gridlines are hairline and recessive. Each chart has a
hover tooltip, and the report shows the same numbers in a table beside it.
"""

from collections.abc import Sequence

import plotly.graph_objects as go
from plotly.offline import get_plotlyjs

SERIES = "#2a78d6"
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e6e5e0"
FONT = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
BAR_SLOT_PX = 34
LABEL_ROOM = 1.22  # axis extent as a multiple of the largest bar
CONFIG = {"displaylogo": False, "responsive": True, "displayModeBar": False}


def plotly_script() -> str:
    """Return the Plotly library source, so the report works offline.

    Returns:
        str: The minified plotly.js source, to inline once in a ``<script>`` tag.
    """
    script: str = get_plotlyjs()
    return script


def horizontal_bars(
    labels: Sequence[str], values: Sequence[float], value_format: str, value_name: str
) -> str:
    """Render a single-series horizontal bar chart, largest bar at the top.

    Args:
        labels (Sequence[str]): Category label for each bar, in display order (top first).
        values (Sequence[float]): Bar values; negative values extend left of zero.
        value_format (str): d3 format for values, e.g. ``",.0f"`` or ``".1%"``.
        value_name (str): Measure name shown in the tooltip, e.g. ``"Revenue (TRY)"``.

    Returns:
        str: An HTML ``<div>`` with the chart, without the Plotly library.
    """
    figure = go.Figure(
        go.Bar(
            x=list(values),
            y=list(labels),
            orientation="h",
            marker={"color": SERIES, "cornerradius": 4},
            texttemplate=f"%{{x:{value_format}}}",
            textposition="outside",
            textfont={"color": TEXT_SECONDARY},
            cliponaxis=False,
            hovertemplate=f"%{{y}}<br>{value_name}: %{{x:{value_format}}}<extra></extra>",
        )
    )
    figure.update_yaxes(autorange="reversed", showgrid=False, ticks="")
    # Leave room past the longest bar for its outside value label.
    low, high = min(0.0, *values), max(0.0, *values)
    figure.update_xaxes(
        tickformat=value_format,
        zeroline=True,
        zerolinecolor=GRID,
        range=[low * LABEL_ROOM, high * LABEL_ROOM],
    )
    return _render(figure, height=len(labels) * BAR_SLOT_PX + 70, bargap=0.4)


def line(x: Sequence[object], y: Sequence[float], value_format: str, value_name: str) -> str:
    """Render a single-series line chart with a hover crosshair.

    Args:
        x (Sequence[object]): X values, e.g. dates, in order.
        y (Sequence[float]): Y values.
        value_format (str): d3 format for values, e.g. ``",.0f"``.
        value_name (str): Measure name shown in the tooltip.

    Returns:
        str: An HTML ``<div>`` with the chart, without the Plotly library.
    """
    figure = go.Figure(
        go.Scatter(
            x=list(x),
            y=list(y),
            mode="lines+markers",
            line={"color": SERIES, "width": 2},
            marker={"color": SERIES, "size": 8, "line": {"color": SURFACE, "width": 2}},
            hovertemplate=(
                f"%{{x|%a %d %b %Y}}<br>{value_name}: %{{y:{value_format}}}<extra></extra>"
            ),
        )
    )
    figure.update_yaxes(tickformat=value_format, rangemode="tozero")
    figure.update_xaxes(
        showgrid=False, showspikes=True, spikemode="across", spikecolor=GRID, spikethickness=1
    )
    return _render(figure, height=320)


def _render(figure: go.Figure, height: int, bargap: float | None = None) -> str:
    """Apply the shared chart styling and render to an HTML fragment.

    Args:
        figure (go.Figure): The chart to render.
        height (int): Chart height in pixels.
        bargap (float | None): Gap between bars as a fraction of the slot; None for
            non-bar charts.

    Returns:
        str: An HTML ``<div>`` with the chart, without the Plotly library.
    """
    figure.update_layout(
        height=height,
        margin={"l": 8, "r": 64, "t": 8, "b": 8},
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font={"family": FONT, "size": 13, "color": TEXT_SECONDARY},
        hoverlabel={"bgcolor": "white", "font": {"color": TEXT_PRIMARY}},
        showlegend=False,
        bargap=bargap,
    )
    figure.update_xaxes(gridcolor=GRID, gridwidth=1, linecolor=GRID, automargin=True)
    figure.update_yaxes(gridcolor=GRID, gridwidth=1, linecolor=GRID, automargin=True)
    html: str = figure.to_html(full_html=False, include_plotlyjs=False, config=CONFIG)
    return html
