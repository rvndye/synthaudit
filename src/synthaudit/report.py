"""Report generation: self-contained HTML, PDF scorecard, companion notebook."""

from __future__ import annotations

import html
import json

SEV_COLOR = {"critical": "#c0392b", "high": "#e67e22", "medium": "#f1c40f", "low": "#95a5a6"}
PILLAR_NAMES = {
    "L": "Label integrity",
    "F": "Feature integrity",
    "H": "Difficulty headroom",
    "R": "Sampling realism",
    "I": "Information density",
    "T": "Transparency",
}
GRADE_COLOR = {"A": "#27ae60", "B": "#2ecc71", "C": "#f1c40f", "D": "#e67e22", "F": "#c0392b"}


def _esc(x):
    return html.escape(str(x))


def _table(rows, cols, limit=None):
    if not rows:
        return "<p class='muted'>none</p>"
    rows = rows[:limit] if limit else rows
    head = "".join(f"<th>{_esc(c)}</th>" for c in cols)
    body = ""
    for r in rows:
        body += "<tr>" + "".join(f"<td>{_esc(r.get(c, ''))}</td>" for c in cols) + "</tr>"
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def render_html(res: dict, path: str):
    meta = res.get("meta", {})
    ident = res.get("identity", {})
    det = res.get("determinism", {})
    cau = res.get("causal", {})
    leak = res.get("leakage", {})
    tax = res.get("taxonomy", {})
    score = res.get("scoring", {})
    rec = res.get("recommendations", {})

    grade = score.get("grade", "?")
    gcol = GRADE_COLOR.get(grade, "#7f8c8d")

    pillar_bars = ""
    for k, v in (score.get("pillars") or {}).items():
        if v is None:
            continue
        pillar_bars += (
            f"<div class='pill'><span class='plabel'>{PILLAR_NAMES.get(k, k)} "
            f"({k})</span><div class='bar'><div class='fill' "
            f"style='width:{v * 100:.0f}%'></div></div>"
            f"<span class='pval'>{v:.2f}</span></div>"
        )

    findings_html = ""
    for f in leak.get("findings", []):
        c = SEV_COLOR.get(f["severity"], "#95a5a6")
        findings_html += (
            f"<div class='finding' style='border-left-color:{c}'>"
            f"<span class='sev' style='background:{c}'>"
            f"{f['severity'].upper()}</span> "
            f"<b>{_esc(f['kind'])}</b><br>{_esc(f['detail'])}</div>"
        )

    id_rows = [
        {
            "type": f["type"],
            "equation": f.get("equation", ""),
            "r2/fidelity": f.get("r2", f.get("fidelity", "")),
            "disposition": f.get("disposition", ""),
            "exact": f.get("exact", ""),
        }
        for f in ident.get("identities", []) + ident.get("rule_derived_labels", [])
    ]
    fd_rows = ident.get("functional_dependencies", [])
    sweep_rows = det.get("sweep", [])[:25]
    tax_rows = [
        {"column": c, "role": r["role"], "why": r.get("why", "")}
        for c, r in (tax.get("roles") or {}).items()
    ]

    doc = f"""<!DOCTYPE html><html><head><meta charset='utf-8'>
<title>SynthAudit — {_esc(meta.get("name"))}</title><style>
body{{font-family:'Segoe UI',system-ui,sans-serif;margin:0;background:#f5f6fa;color:#2c3e50}}
.wrap{{max-width:1080px;margin:0 auto;padding:24px}}
header{{background:#1a252f;color:#ecf0f1;padding:28px 24px;border-radius:0 0 12px 12px}}
h1{{margin:0;font-size:26px}} h2{{margin-top:34px;border-bottom:2px solid #dfe4ea;padding-bottom:6px}}
.sub{{color:#95a5a6;margin-top:6px}}
.cards{{display:flex;gap:16px;flex-wrap:wrap;margin-top:20px}}
.card{{background:#fff;border-radius:10px;padding:16px 20px;box-shadow:0 1px 4px rgba(0,0,0,.08);min-width:130px}}
.card .v{{font-size:24px;font-weight:700}} .card .k{{color:#7f8c8d;font-size:12px;text-transform:uppercase}}
.gradecard{{background:{gcol};color:#fff}}
table{{border-collapse:collapse;width:100%;background:#fff;font-size:13px;margin-top:8px}}
th{{background:#34495e;color:#fff;text-align:left;padding:7px 9px}}
td{{padding:6px 9px;border-bottom:1px solid #ecf0f1;max-width:520px;overflow-wrap:anywhere}}
tr:hover td{{background:#f8f9fb}}
.finding{{background:#fff;border-left:5px solid;#ccc;margin:8px 0;padding:10px 14px;border-radius:6px;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.sev{{color:#fff;font-size:10px;padding:2px 7px;border-radius:9px;margin-right:6px}}
.pill{{display:flex;align-items:center;gap:10px;margin:7px 0}}
.plabel{{width:210px;font-size:13px}} .pval{{font-weight:700;width:44px}}
.bar{{flex:1;height:12px;background:#dfe4ea;border-radius:6px;overflow:hidden}}
.fill{{height:100%;background:linear-gradient(90deg,#e74c3c,#f1c40f 55%,#27ae60);border-radius:6px}}
.muted{{color:#95a5a6}} pre{{background:#fff;padding:12px;border-radius:8px;overflow-x:auto;font-size:12px}}
.rec{{background:#fff;border-radius:8px;padding:12px 16px;margin:8px 0;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
footer{{color:#95a5a6;font-size:12px;margin:40px 0 12px;text-align:center}}
</style></head><body>
<header><div class='wrap'>
<h1>SynthAudit report — {_esc(meta.get("name"))}</h1>
<div class='sub'>{meta.get("n_rows", 0):,} rows × {meta.get("n_cols", 0)} columns
 · target: <b>{_esc(meta.get("target"))}</b> · runtime {meta.get("runtime_s", "?")}s
 · synthaudit v{_esc(meta.get("synthaudit_version", "0"))}</div>
</div></header><div class='wrap'>

<div class='cards'>
<div class='card gradecard'><div class='v'>{grade}</div><div class='k' style='color:#ffffffcc'>BTI grade</div></div>
<div class='card'><div class='v'>{score.get("bti", "—")}</div><div class='k'>BTI score</div></div>
<div class='card'><div class='v'>{ident.get("n_exact", 0)}</div><div class='k'>exact identities</div></div>
<div class='card'><div class='v'>{len(det.get("deterministic", [])) + len(det.get("near_deterministic", []))}</div><div class='k'>(near-)det. columns</div></div>
<div class='card'><div class='v'>{leak.get("n_critical", 0)}</div><div class='k'>critical findings</div></div>
</div>

<h2>Benchmark Trustworthiness Index</h2>{pillar_bars}
<p class='muted'>{_esc(score.get("interpretation", ""))}</p>

<h2>Leakage &amp; artifact findings</h2>{findings_html or "<p class='muted'>none</p>"}

<h2>Recovered identities &amp; rules (Module 2)</h2>
{_table(id_rows, ["type", "equation", "r2/fidelity", "disposition", "exact"])}
<h3>Functional dependencies</h3>
{_table(fd_rows, ["determinant", "dependent", "g3_violation_rate", "exact"], 25)}

<h2>Determinism sweep (Module 3, out-of-sample)</h2>
{_table(sweep_rows, ["column", "metric", "score", "class", "best_single_feature"])}

<h2>Causal structure scan (Module 4, advisory)</h2>
<p>Excluded deterministic columns: {_esc(", ".join(cau.get("excluded_deterministic", []) or ["—"]))}</p>
<p>Varsortability (vs recovered graph): <b>{cau.get("varsortability_est", "—")}</b> ·
R²-sortability: <b>{cau.get("r2sortability_est", "—")}</b></p>
{_table(cau.get("pc_edges", []), ["from", "to", "kind"], 40)}
<p class='muted'>{_esc(cau.get("sortability_note", ""))}</p>

<h2>Variable taxonomy</h2>
{_table(tax_rows, ["column", "role", "why"])}

<h2>Recommendations (Module 7)</h2>
<div class='rec'><b>Drop:</b> {_esc(", ".join(rec.get("drop_columns", []) or ["none"]))}</div>
<div class='rec'><b>Quarantine:</b> {_esc(", ".join(rec.get("quarantine_columns", []) or ["none"]))}</div>
<div class='rec'><b>Suggested tasks:</b><br>{"<br>".join(_esc(t) for t in rec.get("suggested_tasks", []))}</div>
<div class='rec'><b>Protocol warnings:</b><br>{"<br>".join(_esc(w) for w in rec.get("protocol_warnings", []) or ["none"])}</div>

<footer>Generated by SynthAudit — audit synthetic datasets before you benchmark on them.</footer>
</div></body></html>"""
    with open(path, "w") as fh:
        fh.write(doc)


def render_pdf(res: dict, path: str):
    """Compact PDF scorecard via matplotlib (no heavy HTML->PDF deps)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    meta, score = res.get("meta", {}), res.get("scoring", {})
    ident, leak = res.get("identity", {}), res.get("leakage", {})
    with PdfPages(path) as pdf:
        fig, axes = plt.subplots(
            2, 1, figsize=(8.27, 11.69), gridspec_kw={"height_ratios": [1, 1.6]}
        )
        ax = axes[0]
        pillars = {k: v for k, v in (score.get("pillars") or {}).items() if v is not None}
        ax.barh(
            list(PILLAR_NAMES.get(k, k) for k in pillars), list(pillars.values()), color="#2c7fb8"
        )
        ax.set_xlim(0, 1)
        ax.set_title(
            f"SynthAudit scorecard — {meta.get('name')}   "
            f"BTI={score.get('bti')} (grade {score.get('grade')})",
            fontsize=12,
            loc="left",
        )
        ax.invert_yaxis()
        ax2 = axes[1]
        ax2.axis("off")
        lines = [
            f"rows={meta.get('n_rows'):,}  cols={meta.get('n_cols')}  target={meta.get('target')}",
            f"exact identities: {ident.get('n_exact', 0)}   "
            f"critical findings: {leak.get('n_critical', 0)}",
            "",
        ]
        for f in (ident.get("identities", []) + ident.get("rule_derived_labels", []))[:14]:
            lines.append(f"[{f['type']}] {f.get('equation', '')[:88]}")
        lines.append("")
        for f in leak.get("findings", [])[:10]:
            lines.append(f"({f['severity']}) {f['detail'][:92]}")
        ax2.text(
            0.01,
            0.98,
            "\n".join(lines),
            va="top",
            family="monospace",
            fontsize=8,
            transform=ax2.transAxes,
            wrap=True,
        )
        pdf.savefig(fig)
        plt.close(fig)


def render_notebook(res: dict, name: str, target, path: str):
    """Companion notebook that reproduces the audit."""
    import nbformat as nbf

    nb = nbf.v4.new_notebook()
    nb.cells = [
        nbf.v4.new_markdown_cell(
            f"# SynthAudit companion notebook — {name}\n"
            f"Reproduces the audit. Findings summary is embedded below."
        ),
        nbf.v4.new_code_cell(
            "import pandas as pd\nfrom synthaudit import Audit\n\n"
            f"df = pd.read_csv('{name}.csv')  # adjust path\n"
            f"audit = Audit(df, target={target!r}, name={name!r})\n"
            "results = audit.run()\n"
            "audit.generate_report()"
        ),
        nbf.v4.new_markdown_cell("## Findings snapshot (from the original run)"),
        nbf.v4.new_code_cell(
            "findings = "
            + json.dumps(res.get("leakage", {}).get("findings", []), indent=1, default=str)
            + "\nfindings"
        ),
        nbf.v4.new_code_cell(
            "bti = " + json.dumps(res.get("scoring", {}), indent=1, default=str) + "\nbti"
        ),
    ]
    with open(path, "w") as fh:
        nbf.write(nb, fh)
