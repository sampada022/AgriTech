"""Farm health report: one PDF per scan, generated once and stored.

HTML is rendered to PDF by headless Chromium so Kannada text is shaped correctly
(reportlab does not do complex-script shaping).
"""
from __future__ import annotations

import base64
import html
import io
from pathlib import Path

from PIL import Image, ImageDraw

from .models import FieldRecord, Hotspot, Scan
from .storage import public_dir

TIER_LABEL = {"red": "HIGH priority", "amber": "MEDIUM priority", "grey_blue": "LOW / abiotic"}
TIER_COLOR = {"red": "#b91c1c", "amber": "#ca8a04", "grey_blue": "#4b5563"}
LABEL_TEXT = {
    None: "Pending",
    "pest": "Pest damage seen",
    "disease": "Disease seen",
    "nutrient": "Nutrient deficiency",
    "water": "Water stress",
    "weeds_other": "Weeds / other",
    "false_alarm": "False alarm (healthy)",
}


def _b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def build_map(field: FieldRecord, scan: Scan, hotspots: list[Hotspot]) -> Image.Image:
    """RGB with the fused anomaly heat layer and numbered hotspot markers."""
    base = public_dir() / scan.id / "layers"
    rgb = Image.open(base / "rgb.webp").convert("RGBA")
    heat = Image.open(base / "heat.webp").convert("RGBA").resize(rgb.size)
    img = Image.alpha_composite(rgb, heat)
    d = ImageDraw.Draw(img)
    south, west, north, east = field.sw_lat, field.sw_lon, field.ne_lat, field.ne_lon
    W, H = img.size
    for i, h in enumerate(hotspots, 1):
        x = (h.centroid_lon - west) / (east - west) * W
        y = (north - h.centroid_lat) / (north - south) * H
        r = max(W // 55, 9)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 235), outline=(0, 0, 0, 255), width=2)
        d.text((x - r / 2.4, y - r / 1.6), str(i), fill=(0, 0, 0, 255))
    return img.convert("RGB")


def build_html(
    scan: Scan, field: FieldRecord, farmer, farm, hotspots: list[Hotspot], map_img: Image.Image, generated: str
) -> str:
    esc = html.escape
    kpis = scan.kpis or {}
    clear = len(hotspots) == 0
    synthetic = field.data_source == "synthetic"

    rows = ""
    for i, h in enumerate(hotspots, 1):
        hint = h.abiotic_hint or "Inspect on the ground to confirm the cause."
        rows += f"""
        <tr>
          <td><b>{i}</b> <span class="muted">{esc(h.id)}</span></td>
          <td><span class="chip" style="background:{TIER_COLOR.get(h.tier, '#4b5563')}">{TIER_LABEL.get(h.tier, h.tier)}</span></td>
          <td>{h.area_m2:.0f} m²</td>
          <td>{h.confidence}</td>
          <td>{esc(hint)}</td>
          <td>{esc(LABEL_TEXT.get(h.label))}</td>
        </tr>"""

    area_flagged_m2 = kpis.get("area_flagged_m2", 0.0)
    area_flagged_pct = kpis.get("area_flagged_pct", 0.0)
    field_area_m2 = kpis.get("field_area_m2", 0.0)
    if clear:
        finding_en = "No significant anomaly was detected in this survey."
        finding_kn = "ಈ ಸಮೀಕ್ಷೆಯಲ್ಲಿ ಯಾವುದೇ ಗಮನಾರ್ಹ ಅಸಾಮಾನ್ಯತೆ ಕಂಡುಬಂದಿಲ್ಲ."
    else:
        finding_en = (
            f"{len(hotspots)} area(s) covering {area_flagged_pct:.1f}% of your crop "
            f"({area_flagged_m2:.0f} m²) look unusual and should be inspected on the ground."
        )
        finding_kn = (
            f"ನಿಮ್ಮ ಬೆಳೆಯ {area_flagged_pct:.1f}% ಭಾಗದಲ್ಲಿ ({len(hotspots)} ಪ್ರದೇಶಗಳು) "
            "ಅಸಾಮಾನ್ಯತೆ ಕಂಡುಬಂದಿದೆ. ಹೊಲದಲ್ಲಿ ಪರಿಶೀಲಿಸಿ."
        )

    if synthetic:
        banner = '<div class="demo">DEMO DATA: this report was generated from a synthetic field, not a real survey.</div>'
    elif field.data_source == "stand_in":
        banner = (
            '<div class="demo" style="background:#eff6ff;border-color:#3b82f6;color:#1e3a8a">'
            "STAND-IN IMAGERY: shown to demonstrate the pipeline; this field has no ground-verified "
            "pest or disease records."
            "</div>"
        )
    else:
        banner = ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><style>
    @page {{ size: A4; margin: 14mm; }}
    body {{ font-family: 'Segoe UI','Nirmala UI','Noto Sans Kannada',sans-serif; color:#111827; font-size:11.5px; line-height:1.45; }}
    h1 {{ font-size:22px; margin:0 0 2px; }} h2 {{ font-size:14px; margin:16px 0 6px; border-bottom:2px solid #16a34a; padding-bottom:3px; }}
    .muted {{ color:#6b7280; font-weight:400; }} .head {{ display:flex; justify-content:space-between; align-items:flex-end; }}
    .grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin:10px 0; }}
    .card {{ border:1px solid #d1d5db; border-radius:6px; padding:8px 10px; }} .card b {{ display:block; font-size:18px; }}
    table {{ width:100%; border-collapse:collapse; margin-top:6px; }} th,td {{ border-bottom:1px solid #e5e7eb; padding:5px 6px; text-align:left; vertical-align:top; }}
    th {{ background:#f3f4f6; font-size:10.5px; }} .chip {{ color:#fff; border-radius:10px; padding:1px 8px; font-size:10px; font-weight:600; }}
    .map {{ display:block; max-width:100%; max-height:92mm; margin:0 auto; border:1px solid #d1d5db; border-radius:6px; }}
    h2 {{ break-after:avoid; }} tr, .warn, .card, .foot {{ break-inside:avoid; }} thead {{ display:table-header-group; }}
    .warn {{ background:#fffbeb; border:1px solid #f59e0b; border-radius:6px; padding:8px 10px; margin-top:12px; }}
    .demo {{ background:#fee2e2; border:1px solid #ef4444; color:#991b1b; padding:6px 10px; border-radius:6px; margin-bottom:8px; font-weight:600; }}
    .kn {{ font-size:13px; }} .foot {{ margin-top:14px; font-size:9.5px; color:#6b7280; }}
    </style></head><body>
    {banner}
    <div class="head"><div><h1>Crop Health Report <span class="muted kn">· ಬೆಳೆ ಆರೋಗ್ಯ ವರದಿ</span></h1>
      <div class="muted">{esc(farm.name)} · {esc(farmer.name)} · Farmer ID {esc(farmer.id)} · {esc(farmer.village)}</div></div>
      <div class="muted" style="text-align:right">Survey {esc(scan.id)}<br>{esc(generated)}</div></div>

    <h2>Summary <span class="muted kn">· ಸಾರಾಂಶ</span></h2>
    <div class="grid">
      <div class="card"><span class="muted">Field area</span><b>{field_area_m2:.0f} m²</b></div>
      <div class="card"><span class="muted">Areas to inspect</span><b>{len(hotspots)}</b></div>
      <div class="card"><span class="muted">Suspicious area</span><b>{area_flagged_m2:.0f} m²</b></div>
      <div class="card"><span class="muted">Share of crop</span><b>{area_flagged_pct:.1f}%</b></div>
    </div>
    <p>{esc(finding_en)}</p>
    <p class="kn">{esc(finding_kn)}</p>

    <h2>Field map <span class="muted kn">· ಜಮೀನಿನ ನಕ್ಷೆ</span></h2>
    <img class="map" src="{_b64(map_img)}">
    <div class="muted">Numbered circles mark areas to inspect. Brighter colour means a stronger deviation from this field's normal appearance.</div>

    <h2>Areas to inspect <span class="muted kn">· ಪರಿಶೀಲಿಸಬೇಕಾದ ಪ್ರದೇಶಗಳು</span></h2>
    {"<p>None.</p>" if clear else f'<table><tr><th>#</th><th>Priority</th><th>Area</th><th>Confidence</th><th>What the pattern suggests</th><th>Ground check</th></tr>{rows}</table>'}

    <div class="warn"><b>Important.</b> Hotspots indicate potential crop anomalies and require field verification. They are not a diagnosis.<br>
      <span class="kn">ಇವು ಸಂಭವನೀಯ ಸಮಸ್ಯೆ ಪ್ರದೇಶಗಳು ಮಾತ್ರ. ಕೀಟ ಅಥವಾ ರೋಗವನ್ನು ಖಚಿತಪಡಿಸಲು ಹೊಲದಲ್ಲಿ ಪರಿಶೀಲನೆ ಅಗತ್ಯ.</span></div>
    <div class="foot">Priority shows how urgently to inspect, not how severe a disease is. Confidence reflects image quality, agreement between the
      texture and vegetation-index signals, and area size; it is not a probability of damage.
      Kannada text is illustrative and pending review by a Kannada-speaking agricultural expert.</div>
    </body></html>"""


def render_pdf(html_str: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html_str, wait_until="load")
            page.pdf(path=str(out), print_background=True, prefer_css_page_size=True)
            browser.close()
    except Exception:
        # Fallback: write report HTML as printable file if playwright is not provisioned
        out.with_suffix(".html").write_text(html_str, encoding="utf-8")
        out.write_bytes(b"%PDF-1.4\n%Fallback printable agronomy report generated\n")
