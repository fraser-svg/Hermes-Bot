#!/usr/bin/env python3
"""Hermes Mission Control (localhost dashboard).

Run:
  python3 mission_control.py
Then open:
  http://127.0.0.1:8787
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

BASE = Path(__file__).resolve().parent
PROSPECTS_DIR = BASE / "prospects"
OUTPUT_DIR = BASE / "output"
BUILD_REPORT = BASE / "build_report.json"
STRATEGY_DOC = BASE / "STRATEGY_BUILD_FIRST_PITCH_NEVER.md"
CHANGELOG = BASE / "CHANGELOG.md"


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def list_files(pattern: str):
    return sorted(BASE.glob(pattern))


def safe_len_json_array(path: Path) -> int:
    data = read_json(path, [])
    return len(data) if isinstance(data, list) else 0


def aggregate_metrics() -> dict:
    prospect_files = sorted(PROSPECTS_DIR.glob("*.json")) if PROSPECTS_DIR.exists() else []
    poor_files = [p for p in prospect_files if "poor-websites" in p.name]
    no_site_files = [p for p in prospect_files if "poor-websites" not in p.name and "-builds" not in p.name]
    builds_files = [p for p in prospect_files if p.name.endswith("-builds.json")]

    leads_no_site = sum(safe_len_json_array(p) for p in no_site_files)
    leads_poor_site = sum(safe_len_json_array(p) for p in poor_files)

    built_success = 0
    built_failed = 0
    built_total = 0
    for bf in builds_files:
        rows = read_json(bf, [])
        if not isinstance(rows, list):
            continue
        for r in rows:
            built_total += 1
            if r.get("success") is True:
                built_success += 1
            else:
                built_failed += 1

    output_html_count = len(list(OUTPUT_DIR.glob("*.html"))) if OUTPUT_DIR.exists() else 0

    build_report = read_json(BUILD_REPORT, {})
    validation = (build_report or {}).get("validation", {})
    readability = (build_report or {}).get("readability", {})
    val_score = validation.get("score", "unknown")
    val_total = validation.get("total")
    val_passed = validation.get("passed")
    read_pass = readability.get("pass")

    latest_build_ok = bool(val_total == 15 and val_passed == 15 and read_pass is True)

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "kpi_targets": {
            "qualified_leads": 30,
            "websites_built": 10,
            "approved_outreach": 10,
            "conversions": 1,
        },
        "kpi_actual": {
            "qualified_leads": leads_no_site + leads_poor_site,
            "qualified_leads_no_website": leads_no_site,
            "qualified_leads_poor_website": leads_poor_site,
            "websites_built_success": built_success,
            "websites_built_failed": built_failed,
            "website_build_attempts": built_total,
            "output_html_files": output_html_count,
            "approved_outreach": 0,
            "conversions": 0,
        },
        "latest_build_report": {
            "validation_score": val_score,
            "validation_passed": val_passed,
            "validation_total": val_total,
            "readability_pass": read_pass,
            "is_15_of_15_and_readable": latest_build_ok,
            "warnings": readability.get("warnings", []),
        },
        "files": {
            "prospect_files": [str(p.name) for p in prospect_files],
            "build_files": [str(p.name) for p in builds_files],
            "poor_website_files": [str(p.name) for p in poor_files],
        },
    }


def infer_components() -> list[dict]:
    checks = [
        ("Prospecting engine", BASE / "prospect.py", "Core Google Maps no-website detection"),
        ("Build orchestrator", BASE / "run.py", "One-command prospect + build flow"),
        ("Website generator", BASE / "generate.py", "Gemini 3.1 Pro website generation pipeline"),
        ("Poor-website auditor v1", BASE / "prospect_poor_websites.py", "Website quality lane (heuristic)"),
        ("Poor-website auditor v2", BASE / "prospect_poor_websites_v2.py", "Weighted rubric + evidence + confidence + Firecrawl"),
        ("Mission control", BASE / "mission_control.py", "Local dashboard and JSON API"),
        ("Strategy doc", STRATEGY_DOC, "Build-first operating vision"),
        ("Changelog", CHANGELOG, "System evolution log"),
    ]

    out = []
    for name, path, purpose in checks:
        out.append({
            "name": name,
            "path": str(path.relative_to(BASE)),
            "exists": path.exists(),
            "purpose": purpose,
        })
    return out


def render_architecture_map(metrics: dict, status: dict) -> str:
    k = metrics["kpi_actual"]
    latest = metrics["latest_build_report"]

    # Health classes: healthy, warning, broken, shadow
    discover_health = "healthy" if k["qualified_leads"] >= 10 else ("warning" if k["qualified_leads"] > 0 else "shadow")
    fix_health = "healthy" if latest["is_15_of_15_and_readable"] else ("warning" if k["websites_built_success"] > 0 else "shadow")
    outreach_health = "healthy" if k["approved_outreach"] >= 10 else ("warning" if k["approved_outreach"] > 0 else "shadow")
    convert_health = "healthy" if k["conversions"] >= 1 else "shadow"
    maintain_health = "shadow"
    upsell_health = "shadow"
    cancel_health = "shadow"

    engine_health = "healthy" if (BASE / "prospect.py").exists() else "shadow"
    auditor_health = "healthy" if (BASE / "prospect_poor_websites_v2.py").exists() else "shadow"
    generator_health = "healthy" if (BASE / "generate.py").exists() else "shadow"
    quality_health = "healthy" if latest["is_15_of_15_and_readable"] else "broken"
    outreach_sys_health = "shadow"
    billing_health = "shadow"

    return f"""
    <style>
      .arch-wrap {{ background:#0b1222; border:1px solid #22304d; border-radius:14px; padding:14px; overflow:auto; }}
      .arch {{ position:relative; min-width:1060px; min-height:500px; }}
      .node {{ position:absolute; width:210px; border-radius:14px; padding:10px; border:1px solid; box-shadow:0 8px 24px rgba(0,0,0,.25); }}
      .node h4 {{ margin:0 0 6px 0; font-size:14px; }}
      .node .meta {{ font-size:12px; color:#cbd5e1; }}
      .healthy {{ background:#08311f; border-color:#166534; }}
      .warning {{ background:#2b1a04; border-color:#92400e; }}
      .broken {{ background:#3b0a0a; border-color:#7f1d1d; }}
      .shadow {{ background:#111827; border-color:#334155; opacity:.42; filter:grayscale(35%); }}
      .lane-title {{ position:absolute; font-size:12px; color:#94a3b8; text-transform:uppercase; letter-spacing:.08em; }}
      .arrow {{ position:absolute; height:2px; background:#3b4a6b; }}
      .arrow:after {{ content:''; position:absolute; right:-6px; top:-4px; border-top:5px solid transparent; border-bottom:5px solid transparent; border-left:7px solid #3b4a6b; }}
      .v-arrow {{ position:absolute; width:2px; background:#3b4a6b; }}
      .v-arrow:after {{ content:''; position:absolute; left:-4px; bottom:-6px; border-left:5px solid transparent; border-right:5px solid transparent; border-top:7px solid #3b4a6b; }}
      .legend {{ display:flex; gap:10px; flex-wrap:wrap; margin:10px 0 0 0; font-size:12px; }}
      .pill {{ padding:3px 8px; border-radius:999px; border:1px solid #334155; }}
    </style>
    <div class='arch-wrap'>
      <div class='arch'>
        <div class='lane-title' style='left:20px;top:6px'>Customer Lifecycle</div>
        <div class='lane-title' style='left:20px;top:260px'>System Components</div>

        <div class='node {discover_health}' style='left:20px;top:34px'>
          <h4>1) Discover customers</h4><div class='meta'>{k['qualified_leads']} leads found</div>
        </div>
        <div class='node {fix_health}' style='left:245px;top:34px'>
          <h4>2) Fix problems</h4><div class='meta'>{k['websites_built_success']} built / {k['websites_built_failed']} failed</div>
        </div>
        <div class='node {outreach_health}' style='left:470px;top:34px'>
          <h4>3) Outreach</h4><div class='meta'>{k['approved_outreach']} approved</div>
        </div>
        <div class='node {convert_health}' style='left:695px;top:34px'>
          <h4>4) Convert</h4><div class='meta'>{k['conversions']} paying clients</div>
        </div>
        <div class='node {maintain_health}' style='left:920px;top:34px'>
          <h4>5) Maintain</h4><div class='meta'>not started</div>
        </div>
        <div class='node {upsell_health}' style='left:920px;top:128px'>
          <h4>6) Upsell</h4><div class='meta'>not started</div>
        </div>
        <div class='node {cancel_health}' style='left:920px;top:222px'>
          <h4>7) Cancel unpaid</h4><div class='meta'>not started</div>
        </div>

        <div class='arrow' style='left:230px;top:84px;width:18px'></div>
        <div class='arrow' style='left:455px;top:84px;width:18px'></div>
        <div class='arrow' style='left:680px;top:84px;width:18px'></div>
        <div class='arrow' style='left:905px;top:84px;width:18px'></div>
        <div class='v-arrow' style='left:1024px;top:116px;height:22px'></div>
        <div class='v-arrow' style='left:1024px;top:210px;height:22px'></div>

        <div class='node {engine_health}' style='left:20px;top:288px'>
          <h4>prospect.py</h4><div class='meta'>Google Maps no-website lane</div>
        </div>
        <div class='node {auditor_health}' style='left:245px;top:288px'>
          <h4>prospect_poor_websites_v2.py</h4><div class='meta'>Firecrawl + weighted audit</div>
        </div>
        <div class='node {generator_health}' style='left:470px;top:288px'>
          <h4>generate.py</h4><div class='meta'>Gemini 3.1 Pro site builder</div>
        </div>
        <div class='node {quality_health}' style='left:695px;top:288px'>
          <h4>Quality gate</h4><div class='meta'>{metrics['latest_build_report']['validation_score']} / readability={metrics['latest_build_report']['readability_pass']}</div>
        </div>
        <div class='node {outreach_sys_health}' style='left:920px;top:288px'>
          <h4>Outreach logger</h4><div class='meta'>not built</div>
        </div>
        <div class='node {billing_health}' style='left:920px;top:382px'>
          <h4>Billing/churn automation</h4><div class='meta'>not built</div>
        </div>

        <div class='arrow' style='left:230px;top:338px;width:18px'></div>
        <div class='arrow' style='left:455px;top:338px;width:18px'></div>
        <div class='arrow' style='left:680px;top:338px;width:18px'></div>
        <div class='arrow' style='left:905px;top:338px;width:18px'></div>
        <div class='v-arrow' style='left:1024px;top:370px;height:22px'></div>
      </div>
      <div class='legend'>
        <span class='pill healthy'>healthy (built + good)</span>
        <span class='pill warning'>warning (built + partial)</span>
        <span class='pill broken'>broken (built + failing quality)</span>
        <span class='pill shadow'>shadow (not started)</span>
      </div>
    </div>
    """


def render_app_page(mode: str, payload: dict) -> str:
    payload_json = json.dumps(payload).replace("</", "<\\/")
    template = """<!doctype html>
<html>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1' />
  <title>Hermes Mission Control</title>
  <script src='https://cdn.tailwindcss.com'></script>
</head>
<body class='bg-slate-950 text-slate-100 min-h-screen'>
  <div id='app'></div>
  <script id='payload' type='application/json'>__PAYLOAD__</script>
  <script type='module'>
    import React from 'https://esm.sh/react@18';
    import {createRoot} from 'https://esm.sh/react-dom@18/client';
    import htm from 'https://esm.sh/htm@3';
    import {
      HeroUIProvider, Navbar, NavbarBrand, NavbarContent, NavbarItem, Link,
      Card, CardHeader, CardBody, Chip, Code
    } from 'https://esm.sh/@heroui/react?bundle';

    const html = htm.bind(React.createElement);
    const payload = JSON.parse(document.getElementById('payload').textContent);

    const badgeColor = (status) => status === 'built' ? 'success' : (status === 'in_progress' ? 'warning' : 'default');

    function Shell({active, children, updated}) {
      return html`
        <${HeroUIProvider}>
          <div className="min-h-screen bg-slate-950 text-slate-100">
            <${Navbar} maxWidth="xl" isBordered className="bg-slate-900/80 border-slate-800">
              <${NavbarBrand}><p className="font-semibold">Hermes Mission Control</p><//>
              <${NavbarContent} justify="end">
                <${NavbarItem}><${Link} href="/" color=${active==='dashboard'?'primary':'foreground'}>Dashboard<//><//>
                <${NavbarItem}><${Link} href="/vision" color=${active==='vision'?'primary':'foreground'}>Vision<//><//>
                <${NavbarItem}><${Link} href="/api/status" color="foreground">JSON<//><//>
              <//>
            <//>
            <main className="max-w-6xl mx-auto px-4 py-6 space-y-4">
              <p className="text-xs text-slate-400">Updated: ${updated}</p>
              ${children}
            </main>
          </div>
        <//>
      `;
    }

    function Dashboard() {
      const m = payload.metrics;
      const s = payload.status;
      const k = m.kpi_actual;
      return html`
        <${Shell} active="dashboard" updated=${m.generated_at}>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
            ${['Qualified leads','Websites built (success)','Approved outreach','Conversions'].map((t, i)=> html`
              <${Card} className="bg-slate-900 border border-slate-800" shadow="sm">
                <${CardBody}>
                  <div className="text-xs uppercase tracking-wide text-slate-400">${t}</div>
                  <div className="text-3xl font-bold mt-1">${[`${k.qualified_leads} / 30`, `${k.websites_built_success} / 10`, `${k.approved_outreach} / 10`, `${k.conversions} / 1`][i]}</div>
                <//>
              <//>
            `)}
          </div>

          <${Card} className="bg-slate-900 border border-slate-800" shadow="sm">
            <${CardHeader}><h3 className="font-semibold">Pipeline health</h3><//>
            <${CardBody}>
              <p className="text-sm">Latest build report: <${Code}>${m.latest_build_report.validation_score}</${Code}>, readability: <${Code}>${String(m.latest_build_report.readability_pass)}</${Code}></p>
              <p className="text-xs text-slate-400 mt-1">Needs 15/15 + readability PASS for delivery.</p>
            <//>
          <//>

          <${Card} className="bg-slate-900 border border-slate-800" shadow="sm">
            <${CardHeader}><h3 className="font-semibold">Lifecycle phases</h3><//>
            <${CardBody} className="space-y-2">
              ${s.phases.map(p => html`
                <div className="flex items-start justify-between gap-3 border-b border-slate-800 pb-2">
                  <div>
                    <div className="font-medium">${p.phase}</div>
                    <div className="text-xs text-slate-400">${p.progress} • ${p.notes}</div>
                  </div>
                  <${Chip} size="sm" color=${badgeColor(p.status)} variant="flat">${p.status.replace('_',' ')}</${Chip}>
                </div>
              `)}
            <//>
          <//>

          <${Card} className="bg-slate-900 border border-slate-800" shadow="sm">
            <${CardHeader}><h3 className="font-semibold">Broken now</h3><//>
            <${CardBody}>
              ${s.broken.length ? html`<ul className="list-disc pl-5 text-sm text-rose-200 space-y-1">${s.broken.map(b => html`<li>${b}</li>`)}</ul>` : html`<p className="text-sm text-emerald-300">No broken components detected.</p>`}
            <//>
          <//>
        <//>
      `;
    }

    function Vision() {
      const v = payload.vision;
      return html`
        <${Shell} active="vision" updated=${v.generated_at}>
          <${Card} className="bg-slate-900 border border-slate-800" shadow="sm">
            <${CardHeader}><h3 className="font-semibold">Visual architecture map</h3><//>
            <${CardBody}>
              <p className="text-xs text-slate-400 mb-2">Built nodes colored by health. Unbuilt nodes shown as shadows.</p>
              <div dangerouslySetInnerHTML=${{__html: v.architecture_html}} />
            <//>
          <//>

          <${Card} className="bg-slate-900 border border-slate-800" shadow="sm">
            <${CardHeader}><h3 className="font-semibold">Vision we are moving toward</h3><//>
            <${CardBody}><pre className="whitespace-pre-wrap text-sm bg-slate-950 border border-slate-800 rounded-lg p-3 max-h-[420px] overflow-auto">${v.strategy_text}</pre><//>
          <//>

          <${Card} className="bg-slate-900 border border-slate-800" shadow="sm">
            <${CardHeader}><h3 className="font-semibold">Code components actually built</h3><//>
            <${CardBody} className="space-y-2">
              ${v.components.map(c => html`
                <div className="flex items-start justify-between gap-3 border-b border-slate-800 pb-2">
                  <div>
                    <div className="font-medium">${c.name}</div>
                    <div className="text-xs text-slate-400"><code className="text-sky-300">${c.path}</code> • ${c.purpose}</div>
                  </div>
                  <${Chip} size="sm" color=${c.exists ? 'success' : 'default'} variant="flat">${c.exists ? 'built' : 'not started'}</${Chip}>
                </div>
              `)}
            <//>
          <//>

          <${Card} className="bg-slate-900 border border-slate-800" shadow="sm">
            <${CardHeader}><h3 className="font-semibold">Lifecycle execution status</h3><//>
            <${CardBody} className="space-y-2">
              ${v.phases.map(p => html`
                <div className="flex items-start justify-between gap-3 border-b border-slate-800 pb-2">
                  <div>
                    <div className="font-medium">${p.phase}</div>
                    <div className="text-xs text-slate-400">${p.progress} • ${p.notes}</div>
                  </div>
                  <${Chip} size="sm" color=${badgeColor(p.status)} variant="flat">${p.status.replace('_',' ')}</${Chip}>
                </div>
              `)}
            <//>
          <//>

          <${Card} className="bg-slate-900 border border-slate-800" shadow="sm">
            <${CardHeader}><h3 className="font-semibold">What is broken now</h3><//>
            <${CardBody}>
              ${v.broken.length ? html`<ul className="list-disc pl-5 text-sm text-rose-200 space-y-1">${v.broken.map(b => html`<li>${b}</li>`)}</ul>` : html`<p className="text-sm text-emerald-300">No broken components detected.</p>`}
            <//>
          <//>
        <//>
      `;
    }

    const root = createRoot(document.getElementById('app'));
    root.render(payload.mode === 'dashboard' ? html`<${Dashboard} />` : html`<${Vision} />`);
  </script>
</body>
</html>"""
    return template.replace("__PAYLOAD__", payload_json)


def render_vision_page() -> str:
    metrics = aggregate_metrics()
    status = component_status(metrics)
    strategy_text = STRATEGY_DOC.read_text(encoding="utf-8")[:8000] if STRATEGY_DOC.exists() else "Strategy doc not found."
    payload = {
        "mode": "vision",
        "vision": {
            "generated_at": metrics["generated_at"],
            "architecture_html": render_architecture_map(metrics, status),
            "strategy_text": strategy_text,
            "components": infer_components(),
            "phases": status["phases"],
            "broken": status["broken"],
        },
    }
    return render_app_page("vision", payload)


def component_status(metrics: dict) -> dict:
    k = metrics["kpi_actual"]
    latest = metrics["latest_build_report"]

    phases = [
        {
            "phase": "Discover customers",
            "status": "built" if k["qualified_leads"] > 0 else "not_started",
            "progress": f"{k['qualified_leads']} leads discovered",
            "notes": "prospect.py + poor-website v2 active",
        },
        {
            "phase": "Fix their problems",
            "status": "in_progress" if k["websites_built_success"] > 0 else "not_started",
            "progress": f"{k['websites_built_success']} successful builds, {k['websites_built_failed']} failed",
            "notes": "generate.py pipeline only; latest build quality gate applied",
        },
        {
            "phase": "Outreach them",
            "status": "not_started",
            "progress": "0 approved outreach logged",
            "notes": "manual approval gate enabled",
        },
        {
            "phase": "Convert into paying customers",
            "status": "not_started",
            "progress": "0 conversions logged",
            "notes": "await outreach responses",
        },
        {
            "phase": "Maintain clients",
            "status": "not_started",
            "progress": "0 active paying clients",
            "notes": "maintenance workflow pending first conversion",
        },
        {
            "phase": "Upsell clients",
            "status": "not_started",
            "progress": "0 upsells",
            "notes": "trigger after active client base",
        },
        {
            "phase": "Cancel unpaid/cancelled",
            "status": "not_started",
            "progress": "0 cancellations",
            "notes": "billing + churn process pending",
        },
    ]

    broken = []
    if not latest["is_15_of_15_and_readable"]:
        broken.append("Latest website build report is below quality gate (needs 15/15 + readability PASS)")
    if k["websites_built_failed"] > 0:
        broken.append(f"{k['websites_built_failed']} website build attempts marked failed")

    return {"phases": phases, "broken": broken}


HTML_TEMPLATE = """<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Hermes Mission Control</title>
  <script src=\"https://cdn.tailwindcss.com\"></script>
</head>
<body class=\"bg-slate-950 text-slate-100 min-h-screen\">
  <header class=\"border-b border-slate-800 bg-slate-900/80 backdrop-blur\">
    <div class=\"max-w-6xl mx-auto px-4 py-3 flex items-center justify-between\">
      <div class=\"font-semibold\">Hermes Mission Control</div>
      <nav class=\"flex gap-2 text-sm\">
        <a href=\"/\" class=\"px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700\">Dashboard</a>
        <a href=\"/vision\" class=\"px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700\">Vision</a>
        <a href=\"/api/status\" class=\"px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700\">JSON</a>
      </nav>
    </div>
  </header>

  <main class=\"max-w-6xl mx-auto px-4 py-6 space-y-5\">
    <div class=\"text-xs text-slate-400\">Updated: __UPDATED__</div>

    <section>
      <h2 class=\"text-lg font-semibold mb-3\">Progress vs 7-day targets</h2>
      <div class=\"grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3\">
        <div class=\"rounded-xl border border-slate-800 bg-slate-900 p-4\"><div class=\"text-xs uppercase tracking-wider text-slate-400\">Qualified leads</div><div class=\"text-3xl font-bold mt-1\">__LEADS__ / 30</div></div>
        <div class=\"rounded-xl border border-slate-800 bg-slate-900 p-4\"><div class=\"text-xs uppercase tracking-wider text-slate-400\">Websites built (success)</div><div class=\"text-3xl font-bold mt-1\">__BUILDS__ / 10</div></div>
        <div class=\"rounded-xl border border-slate-800 bg-slate-900 p-4\"><div class=\"text-xs uppercase tracking-wider text-slate-400\">Approved outreach</div><div class=\"text-3xl font-bold mt-1\">__OUTREACH__ / 10</div></div>
        <div class=\"rounded-xl border border-slate-800 bg-slate-900 p-4\"><div class=\"text-xs uppercase tracking-wider text-slate-400\">Conversions</div><div class=\"text-3xl font-bold mt-1\">__CONVERSIONS__ / 1</div></div>
      </div>
    </section>

    <section class=\"rounded-xl border border-slate-800 bg-slate-900 p-4\">
      <h2 class=\"text-lg font-semibold mb-1\">Pipeline health</h2>
      <div class=\"text-sm\">Latest build report: <code class=\"text-sky-300\">__VAL_SCORE__</code>, readability pass: <code class=\"text-sky-300\">__READ_PASS__</code></div>
      <div class=\"text-xs text-slate-400 mt-1\">Needs 15/15 + readability PASS for delivery.</div>
    </section>

    <section class=\"rounded-xl border border-slate-800 bg-slate-900 p-4\">
      <h2 class=\"text-lg font-semibold mb-3\">Lifecycle phases</h2>
      __PHASE_ROWS__
    </section>

    <section class=\"rounded-xl border border-slate-800 bg-slate-900 p-4\">
      <h2 class=\"text-lg font-semibold mb-3\">Broken now</h2>
      __BROKEN_ROWS__
    </section>
  </main>
</body>
</html>
"""


def render_dashboard() -> str:
    m = aggregate_metrics()
    s = component_status(m)
    payload = {
        "mode": "dashboard",
        "metrics": m,
        "status": s,
    }
    return render_app_page("dashboard", payload)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/status":
            data = aggregate_metrics()
            data["component_status"] = component_status(data)
            blob = json.dumps(data, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(blob)))
            self.end_headers()
            self.wfile.write(blob)
            return

        if path == "/" or path == "/index.html":
            html = render_dashboard().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return

        if path == "/vision":
            html = render_vision_page().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return

        self.send_response(404)
        self.end_headers()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--print-status", action="store_true", help="Print current status JSON and exit")
    args = parser.parse_args()

    if args.print_status:
        data = aggregate_metrics()
        data["component_status"] = component_status(data)
        print(json.dumps(data, indent=2))
        return 0

    server = HTTPServer((args.host, args.port), Handler)
    print(f"Mission Control running on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    raise SystemExit(main())
