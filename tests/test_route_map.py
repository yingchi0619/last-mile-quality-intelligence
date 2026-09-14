"""Verify the route map's standalone data and iframe packaging."""

import json
from html.parser import HTMLParser

from app.pages.route_risk import MAP_ROOT, build_map_html


def test_embedded_map_has_no_relative_asset_requests():
    class Assets(HTMLParser):
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "script":
                assert "src" not in attrs
            if tag == "link":
                assert attrs.get("rel") != "stylesheet"

    html = build_map_html()
    Assets().feed(html)
    assert "fetch('zip-data.json')" not in html
    assert 'id="zip-data"' in html
    assert "claim_amount" not in html


def test_map_snapshot_completeness_and_known_score():
    features = json.loads((MAP_ROOT / "zip-data.json").read_text())["features"]
    meta = json.loads((MAP_ROOT / "data-meta.json").read_text())
    assert len(features) == meta["counts"]["total"] == 755
    complete = [f for f in features if all(v is not None for v in f["properties"]["scores"])]
    assert len(complete) == meta["counts"]["complete"] == 737
    props = next(f["properties"] for f in features if f["properties"]["zip"] == "11201")
    score = sum(v * w for v, w in zip(props["scores"], [.2, .3, .25, .25]))
    assert round(score, 1) == 92.5
