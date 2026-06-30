"""
Registers the 'diamond_iq' Plotly template.
Most pages now call apply_theme() from src/components.py directly, but this
is kept for any legacy chart code that registers the template globally.
"""

import plotly.graph_objects as go  # type: ignore
import plotly.io as pio  # type: ignore

P = {
    "navy": "#0B3D91",
    "red": "#C8102E",
    "gold": "#E8B923",
    "green": "#2E7D32",
    "neutral": "#4A5568",
    "bg": "#FAFAFA",
    "surface": "#F0F4F8",
    "grid": "#E2E8F0",
    "text": "#1A202C",
    "subtext": "#718096",
}

SERIES_COLORS = [
    P["navy"],
    P["red"],
    P["gold"],
    P["green"],
    "#6A1B9A",
    "#00838F",
    "#E65100",
    "#5D4037",
]


def register_theme() -> None:
    """Register 'diamond_iq' Plotly template. Idempotent."""
    if "diamond_iq" in pio.templates:
        pio.templates.default = "diamond_iq"
        return

    template = go.layout.Template()
    template.layout = go.Layout(
        font=dict(
            family="Inter, -apple-system, Segoe UI, Helvetica Neue, Arial, sans-serif",
            size=13,
            color=P["text"],
        ),
        title=dict(font=dict(size=16, color=P["text"]), x=0.02),
        plot_bgcolor=P["bg"],
        paper_bgcolor="white",
        colorway=SERIES_COLORS,
        xaxis=dict(
            gridcolor=P["grid"],
            zerolinecolor=P["grid"],
            linecolor=P["grid"],
            tickfont=dict(size=12),
        ),
        yaxis=dict(
            gridcolor=P["grid"],
            zerolinecolor=P["grid"],
            linecolor=P["grid"],
            tickfont=dict(size=12),
        ),
        legend=dict(
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor=P["grid"],
            borderwidth=1,
            font=dict(size=12),
        ),
        hoverlabel=dict(
            bgcolor="white",
            bordercolor=P["grid"],
            font=dict(size=12, color=P["text"]),
        ),
        margin=dict(l=55, r=25, t=55, b=50),
    )
    pio.templates["diamond_iq"] = template
    pio.templates.default = "diamond_iq"
