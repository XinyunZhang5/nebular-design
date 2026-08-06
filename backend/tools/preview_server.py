"""Local preview harness for the segmentation -> depth -> legolize pipeline.

Runs the real services from app/services with no database, no auth and no S3, so
you can drop arbitrary photos in and see what the build plan comes out as before
any of it is wired into the upload route.

    cd backend && python tools/preview_server.py
    open http://localhost:8080

Not part of the deployed app — it is a development tool.
"""

from __future__ import annotations

import base64
import io
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import uvicorn
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image

from app.services.depth import estimate_depth_map
from app.services.ldraw import to_ldraw
from app.services.legolize import generate_plan, render_facade, render_massing
from app.services.segment import crop_to_building, segment_building

app = FastAPI(title="Nebular pipeline preview")

MAX_PIXELS = 4_000_000  # keep CPU inference to a few seconds


def _to_data_uri(image: Image.Image, fmt: str = "PNG") -> str:
    """Inline an image as a data URI.

    Photographs go out as JPEG — as PNG they were 1.5 MB each and the page
    stalled on every run. The stud panel stays PNG so its edges stay crisp.
    """
    buf = io.BytesIO()
    if fmt == "JPEG":
        image.convert("RGB").save(buf, format="JPEG", quality=82, optimize=True)
        mime = "image/jpeg"
    else:
        image.save(buf, format="PNG")
        mime = "image/png"
    return f"data:{mime};base64," + base64.b64encode(buf.getvalue()).decode()


def _mask_overlay(image: Image.Image, mask: np.ndarray) -> Image.Image:
    """Original photo with everything that is not the building drained away."""
    rgb = np.asarray(image.convert("RGB"), dtype=np.float32)
    if mask.shape != rgb.shape[:2]:
        mask = (
            np.asarray(
                Image.fromarray(mask.astype(np.uint8) * 255).resize(
                    image.size, Image.Resampling.NEAREST
                )
            )
            > 127
        )
    grey = rgb.mean(axis=2, keepdims=True).repeat(3, axis=2)
    out = np.where(mask[:, :, None], rgb, grey * 0.35)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def _depth_visual(depth: np.ndarray) -> Image.Image:
    d = depth.astype(np.float32)
    lo, hi = float(d.min()), float(d.max())
    norm = (d - lo) / (hi - lo) if hi - lo > 1e-6 else np.zeros_like(d)
    return Image.fromarray((norm * 255).astype(np.uint8)).convert("RGB")


def _on_backdrop(rgba: Image.Image) -> Image.Image:
    """Composite the transparent panel onto a neutral card background."""
    backdrop = Image.new("RGB", rgba.size, (26, 27, 32))
    backdrop.paste(rgba, (0, 0), rgba)
    return backdrop


SEG_MODELS = {
    "nvidia/segformer-b0-finetuned-ade-512-512": "B0 · 3.8M params · 14 MB",
    "nvidia/segformer-b2-finetuned-ade-512-512": "B2 · 27.4M params · 105 MB",
    "nvidia/segformer-b4-finetuned-ade-512-512": "B4 · 64.1M params · 245 MB",
}


@app.post("/api/preview")
async def preview(
    image: UploadFile = File(...),
    max_studs: int = Form(96),
    relief_studs: int = Form(5),
    building_only: bool = Form(True),
    model_name: str = Form("nvidia/segformer-b0-finetuned-ade-512-512"),
):
    if model_name not in SEG_MODELS:
        return JSONResponse({"error": f"Unknown model {model_name!r}"}, status_code=400)
    timings: dict[str, float] = {}
    try:
        raw = await image.read()
        src = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as exc:
        return JSONResponse({"error": f"Could not read that image: {exc}"}, status_code=400)

    if src.width * src.height > MAX_PIXELS:
        scale = (MAX_PIXELS / (src.width * src.height)) ** 0.5
        src = src.resize(
            (max(1, int(src.width * scale)), max(1, int(src.height * scale))),
            Image.Resampling.LANCZOS,
        )

    try:
        t = time.time()
        seg = await segment_building(src, model_name=model_name)
        timings["segment"] = round(time.time() - t, 2)

        t = time.time()
        depth = await estimate_depth_map(src)
        timings["depth"] = round(time.time() - t, 2)

        mask_full = seg["mask"]
        overlay = _mask_overlay(src, mask_full)

        if building_only and seg["building_share"] > 0.01:
            work_img, work_depth, work_mask = crop_to_building(src, depth, mask_full)
        else:
            work_img, work_mask = src, None
            work_depth = np.asarray(
                Image.fromarray(depth, mode="F").resize(src.size, Image.Resampling.BILINEAR),
                dtype=np.float32,
            )

        t = time.time()
        plan = generate_plan(
            work_img,
            work_depth,
            building_mask=work_mask,
            max_studs=max_studs,
            relief_studs=relief_studs,
        )
        timings["legolize"] = round(time.time() - t, 2)
    except Exception as exc:  # surface it instead of silently mocking
        import traceback

        traceback.print_exc()
        return JSONResponse({"error": f"{type(exc).__name__}: {exc}"}, status_code=500)

    grids = plan.pop("_grids")
    gw = max(1, plan["grid"]["width"])
    panel = render_facade(grids["depths"], grids["colours"], scale=max(8, 1600 // gw))
    iso = render_massing(grids["depths"], grids["colours"], scale=max(6, 1200 // gw))
    ldr = to_ldraw(
        grids["cells"], plan["grid"]["width"], plan["grid"]["courses"],
        plan["grid"]["depth"], name="Nebular build",
    )

    return {
        "images": {
            "original": _to_data_uri(src, "JPEG"),
            "segmentation": _to_data_uri(overlay, "JPEG"),
            "depth": _to_data_uri(_depth_visual(depth), "JPEG"),
            "lego": _to_data_uri(_on_backdrop(panel)),
            "isometric": _to_data_uri(_on_backdrop(iso)),
        },
        "ldraw": ldr,
        "plan": plan,
        "segmentation": {
            "buildingShare": round(seg["building_share"], 4),
            "composition": seg["composition"],
            "model": SEG_MODELS[model_name],
        },
        "timings": timings,
    }


PAGE = """
<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nebular pipeline preview</title>
<style>
  :root { color-scheme: dark; --bg:#0e0f13; --card:#16181f; --line:#262a35;
          --ink:#e7e9ee; --dim:#8a90a0; --accent:#ffd166; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
         font:14px/1.55 ui-sans-serif,-apple-system,"Segoe UI",system-ui,sans-serif; }
  header { padding:22px 28px; border-bottom:1px solid var(--line); }
  h1 { margin:0; font-size:17px; letter-spacing:-.01em; font-weight:620; }
  h1 span { color:var(--dim); font-weight:400; }
  main { padding:24px 28px 64px; max-width:1500px; }
  .drop { border:1.5px dashed var(--line); border-radius:12px; padding:38px;
          text-align:center; color:var(--dim); cursor:pointer; transition:.15s;
          background:var(--card); }
  .drop:hover, .drop.over { border-color:var(--accent); color:var(--ink); }
  .controls { display:flex; gap:26px; align-items:center; flex-wrap:wrap;
              margin:20px 0 8px; padding:16px 18px; background:var(--card);
              border:1px solid var(--line); border-radius:12px; }
  .controls label { display:flex; gap:9px; align-items:center; color:var(--dim); }
  .controls output { color:var(--accent); font-variant-numeric:tabular-nums;
                     min-width:2.6em; font-weight:600; }
  input[type=range] { accent-color:var(--accent); width:150px; }
  input[type=checkbox] { accent-color:var(--accent); width:16px; height:16px; }
  select { background:#1e2129; color:var(--ink); border:1px solid var(--line);
           border-radius:7px; padding:5px 8px; font:inherit; font-size:13px; }
  button { background:var(--accent); color:#1a1a1a; border:0; border-radius:8px;
           padding:9px 18px; font:inherit; font-weight:620; cursor:pointer; }
  button:hover { filter:brightness(1.08); }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(310px,1fr));
          gap:16px; margin-top:22px; }
  figure { margin:0; background:var(--card); border:1px solid var(--line);
           border-radius:12px; overflow:hidden; }
  figure img { display:block; width:100%; height:auto; }
  figcaption { padding:10px 13px; font-size:12px; color:var(--dim);
               border-top:1px solid var(--line); }
  .stats { display:grid; grid-template-columns:repeat(auto-fit,minmax(155px,1fr));
           gap:12px; margin-top:22px; }
  .stat { background:var(--card); border:1px solid var(--line); border-radius:12px;
          padding:14px 16px; }
  .stat b { display:block; font-size:23px; font-weight:640; letter-spacing:-.02em;
            font-variant-numeric:tabular-nums; }
  .stat span { font-size:11.5px; color:var(--dim); text-transform:uppercase;
               letter-spacing:.06em; }
  table { width:100%; border-collapse:collapse; margin-top:22px; font-size:13px; }
  th, td { text-align:left; padding:7px 11px; border-bottom:1px solid var(--line); }
  th { color:var(--dim); font-weight:500; font-size:11.5px;
       text-transform:uppercase; letter-spacing:.06em; }
  td.n { text-align:right; font-variant-numeric:tabular-nums; }
  .sw { display:inline-block; width:11px; height:11px; border-radius:3px;
        margin-right:7px; vertical-align:-1px; border:1px solid #0006; }
  .hid { color:var(--dim); }
  .err { background:#2a1417; border:1px solid #5c2a30; color:#ffb3b8;
         padding:13px 16px; border-radius:10px; margin-top:20px; }
  .muted { color:var(--dim); }
  .pill { display:inline-block; background:#1e2129; border:1px solid var(--line);
          border-radius:999px; padding:2px 9px; margin:2px 4px 2px 0; font-size:12px; }
  #busy { display:none; margin-top:20px; color:var(--accent); }
  #busy.on { display:block; }
</style></head><body>
<header><h1>Nebular pipeline preview <span>— segment → depth → legolize</span></h1></header>
<main>
  <div class="drop" id="drop">
    Drop a photo here, or click to choose one
    <input type="file" id="file" accept="image/*" hidden>
  </div>

  <div class="controls">
    <label>Resolution
      <input type="range" id="studs" min="24" max="160" step="8" value="96">
      <output id="studsOut">96</output> studs
    </label>
    <label>Depth
      <input type="range" id="levels" min="1" max="12" step="1" value="5">
      <output id="levelsOut">5</output> studs
    </label>
    <label><input type="checkbox" id="only" checked> Building only (drop sky / trees / ground)</label>
    <label>Segmentation model
      <select id="model">
        <option value="nvidia/segformer-b0-finetuned-ade-512-512">B0 — 14 MB, ~0.5s</option>
        <option value="nvidia/segformer-b2-finetuned-ade-512-512">B2 — 105 MB, ~1.0s</option>
        <option value="nvidia/segformer-b4-finetuned-ade-512-512">B4 — 245 MB, ~1.7s</option>
      </select>
    </label>
  </div>
  <p class="muted" style="margin:-2px 0 0;font-size:12.5px">
    Switching model downloads it the first time. Everything here runs on CPU.
  </p>

  <div id="busy">Running the pipeline… first run downloads the models, give it a minute.</div>
  <div id="out"></div>
</main>
<script>
const $ = s => document.querySelector(s);
const drop = $('#drop'), file = $('#file'), out = $('#out'), busy = $('#busy');
let last = null;

$('#studs').oninput  = e => $('#studsOut').value  = e.target.value;
$('#levels').oninput = e => $('#levelsOut').value = e.target.value;
for (const id of ['#studs','#levels','#only','#model'])
  $(id).onchange = () => last && run(last);

drop.onclick = () => file.click();
file.onchange = e => e.target.files[0] && run(e.target.files[0]);
drop.ondragover = e => { e.preventDefault(); drop.classList.add('over'); };
drop.ondragleave = () => drop.classList.remove('over');
drop.ondrop = e => {
  e.preventDefault(); drop.classList.remove('over');
  const f = [...e.dataTransfer.files].find(f => f.type.startsWith('image/'));
  if (f) run(f);
};

async function run(f) {
  last = f;
  busy.classList.add('on');
  drop.textContent = f.name;
  const fd = new FormData();
  fd.append('image', f);
  fd.append('max_studs', $('#studs').value);
  fd.append('relief_studs', $('#levels').value);
  fd.append('building_only', $('#only').checked ? 'true' : 'false');
  fd.append('model_name', $('#model').value);
  try {
    const res = await fetch('/api/preview', { method:'POST', body: fd });
    const data = await res.json();
    out.innerHTML = res.ok ? render(data)
      : `<div class="err">${escapeHtml(data.error || 'Request failed')}</div>`;
    const dl = $('#dl');
    if (dl) dl.onclick = () => {
      const url = URL.createObjectURL(new Blob([data.ldraw], {type:'text/plain'}));
      const a = document.createElement('a');
      a.href = url;
      a.download = (f.name.replace(/\.[^.]+$/, '') || 'nebular') + '.ldr';
      a.click();
      URL.revokeObjectURL(url);
    };
  } catch (err) {
    out.innerHTML = `<div class="err">${escapeHtml(String(err))}</div>`;
  } finally {
    busy.classList.remove('on');
  }
}

const escapeHtml = s => String(s).replace(/[&<>"']/g,
  c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function render(d) {
  const p = d.plan, g = p.grid, t = d.timings;
  const comp = Object.entries(d.segmentation.composition)
    .map(([k,v]) => `<span class="pill">${escapeHtml(k)} ${(v*100).toFixed(0)}%</span>`).join('');
  const rows = p.bricks.slice(0, 40).map(b => `
    <tr class="${b.hidden ? 'hid' : ''}">
      <td><code>${escapeHtml(b.partId)}</code></td>
      <td>${escapeHtml(b.name)}</td>
      <td><span class="sw" style="background:${swatch(b.colorId)}"></span>${escapeHtml(b.color)}</td>
      <td class="n">${b.quantity}</td>
      <td>${b.hidden ? 'structure' : 'facade'}</td>
    </tr>`).join('');
  return `
  <div class="grid">
    <figure><img src="${d.images.original}"><figcaption>1 — input</figcaption></figure>
    <figure><img src="${d.images.segmentation}"><figcaption>2 — segmentation · ${escapeHtml(d.segmentation.model)} · building = ${(d.segmentation.buildingShare*100).toFixed(1)}% of frame · ${t.segment}s</figcaption></figure>
    <figure><img src="${d.images.depth}"><figcaption>3 — depth · brighter = nearer (${t.depth}s)</figcaption></figure>
    <figure><img src="${d.images.lego}"><figcaption>4 — the model's facade, head-on (${t.legolize}s)</figcaption></figure>
    <figure><img src="${d.images.isometric}"><figcaption>5 — the same model at an angle, so its ${g.depth} studs of depth read</figcaption></figure>
  </div>
  <p style="margin-top:18px">
    <button id="dl">Download .ldr</button>
    <span class="muted" style="margin-left:12px">Open in BrickLink Studio 2.0 (free) for a photoreal render,
    auto-generated step instructions, and one-click parts ordering. LeoCAD and LDView also read it.</span>
  </p>
  <div class="stats">
    <div class="stat"><b>${p.estimatedPieceCount.toLocaleString()}</b><span>total pieces</span></div>
    <div class="stat"><b>${p.visiblePieceCount.toLocaleString()}</b><span>visible</span></div>
    <div class="stat"><b>${p.hiddenPieceCount.toLocaleString()}</b><span>hidden support</span></div>
    <div class="stat"><b>${g.width}×${g.courses}×${g.depth}</b><span>studs · courses · deep</span></div>
    <div class="stat"><b>${g.sizeCm.width}×${g.sizeCm.height}×${g.sizeCm.depth}</b><span>cm, built</span></div>
    <div class="stat"><b>${g.buildingCells.toLocaleString()}</b><span>building cells</span></div>
    <div class="stat"><b>${p.colorPalette.length}</b><span>colours</span></div>
    <div class="stat"><b>${p.difficulty}</b><span>${escapeHtml(p.estimatedTime)}</span></div>
  </div>
  <p class="muted" style="margin-top:20px">Floor: ${p.base.quantity} plates over ${p.base.widthStuds}×${p.base.depthStuds} studs ·
     Structure: ${p.structure.sound ? 'self-supporting' : `${p.structure.spansNeedingSupport} span(s) need reinforcing (longest unsupported run ${p.structure.longestFloatingStuds} studs)`} ·
     Frame contents: ${comp}</p>
  <table>
    <thead><tr><th>Part</th><th>Name</th><th>Colour</th><th class="n">Qty</th><th></th></tr></thead>
    <tbody>${rows}</tbody>
  </table>
  ${p.bricks.length > 40 ? `<p class="muted">…and ${p.bricks.length - 40} more line items.</p>` : ''}`;
}

const SWATCHES = __SWATCHES__;
const swatch = id => SWATCHES[id] || '#888';
</script></body></html>
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    from app.services import lego_catalogue as cat

    swatches = {c.colour_id: "#%02x%02x%02x" % c.rgb for c in cat.COLOURS}
    import json

    return PAGE.replace("__SWATCHES__", json.dumps(swatches))


if __name__ == "__main__":
    print("Preview harness on http://localhost:8080  (Ctrl-C to stop)")
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="warning")
