"""Independent public-data route difficulty map, bundled for local rendering."""

from pathlib import Path
import base64
import json

import pandas as pd
import streamlit.components.v1 as components


MAP_ROOT = Path(__file__).resolve().parents[1] / "route_map"


def build_map_html() -> str:
    html = (MAP_ROOT / "index.html").read_text()
    html = html.replace("</head>", "<style>" + (MAP_ROOT / "dashboard.css").read_text() + "</style></head>")
    html = html.replace('class="brand" href="./"', 'class="brand" href="#"')
    for name in ("vendor/leaflet.css", "style.css"):
        css = (MAP_ROOT / name).read_text()
        if name.startswith("vendor/"):
            for image in (MAP_ROOT / "vendor/images").glob("*.png"):
                uri = "data:image/png;base64," + base64.b64encode(image.read_bytes()).decode()
                css = css.replace(f"images/{image.name}", uri)
        html = html.replace(f'<link rel="stylesheet" href="{name}">', f"<style>{css}</style>")
    # Inline data avoids relative fetch URLs inside Streamlit's srcdoc iframe.
    payload = "\n".join(
        f'<script type="application/json" id="{key}">'
        + json.dumps(json.loads((MAP_ROOT / filename).read_text()), ensure_ascii=False).replace("<", "\\u003c")
        + "</script>"
        for key, filename in [("zip-data", "zip-data.json"), ("data-meta", "data-meta.json")]
    )
    html = html.replace('<script src="vendor/leaflet.js"></script>', payload + "<script>" + (MAP_ROOT / "vendor/leaflet.js").read_text() + "</script>")
    html = html.replace('<script src="app.js"></script>', "<script>" + (MAP_ROOT / "app.js").read_text() + "</script>")
    return html


def render(_routes: pd.DataFrame | None = None) -> None:
    components.html(build_map_html(), height=1100, scrolling=True)
