"""Presentation helpers for browser-based health report rendering."""

from __future__ import annotations

from html import escape

from app.models import HealthEvaluationResponse

SAMPLE_PAYLOAD = """{
  "components": [
    {
      "name": "frontend",
      "health_check_url": "http://frontend/health"
    },
    {
      "name": "api-service",
      "health_check_url": "http://api-service/health"
    },
    {
      "name": "database",
      "health_check_url": "http://database/health"
    }
  ],
  "dependencies": [
    ["frontend", "api-service"],
    ["api-service", "database"]
  ]
}"""


def render_health_report_page() -> str:
    """Render the browser page used to submit JSON and view the HTML report."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Health Report Viewer</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4efe6;
      --panel: #fffdf9;
      --border: #d7cbb9;
      --ink: #221d18;
      --muted: #6e665e;
      --accent: #9a4028;
      --accent-soft: #f5dfd9;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background: radial-gradient(circle at top, #efe4d2 0%, var(--bg) 55%);
      color: var(--ink);
      padding: 28px;
    }}
    .layout {{
      max-width: 1200px;
      margin: 0 auto;
      display: grid;
      gap: 20px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 18px;
      box-shadow: 0 18px 50px rgba(31, 21, 13, 0.08);
      overflow: hidden;
    }}
    .hero {{
      padding: 28px 30px 16px;
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: 34px;
      line-height: 1.1;
    }}
    p {{
      margin: 0;
      color: var(--muted);
      font-size: 16px;
    }}
    .editor {{
      padding: 0 24px 24px;
    }}
    textarea {{
      width: 100%;
      min-height: 320px;
      resize: vertical;
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 18px;
      font: 14px/1.5 Consolas, "Courier New", monospace;
      background: #fffdfa;
      color: var(--ink);
    }}
    .actions {{
      display: flex;
      gap: 12px;
      align-items: center;
      margin-top: 14px;
      flex-wrap: wrap;
    }}
    button {{
      border: 0;
      border-radius: 999px;
      padding: 12px 18px;
      background: var(--accent);
      color: white;
      font: inherit;
      cursor: pointer;
    }}
    .hint {{
      color: var(--muted);
      font-size: 14px;
    }}
    .error {{
      display: none;
      margin: 16px 24px 0;
      padding: 14px 16px;
      border-radius: 12px;
      background: var(--accent-soft);
      color: var(--accent);
      border: 1px solid #e6bdb2;
      white-space: pre-wrap;
      font-family: Consolas, "Courier New", monospace;
      font-size: 14px;
    }}
    iframe {{
      width: 100%;
      min-height: 520px;
      border: 0;
      background: white;
    }}
  </style>
</head>
<body>
  <main class="layout">
    <section class="panel">
      <div class="hero">
        <h1>Health Report Viewer</h1>
        <p>Paste your DAG request JSON and render the health summary as a browser table.</p>
      </div>
      <div id="error" class="error"></div>
      <div class="editor">
        <textarea id="payload">{escape(SAMPLE_PAYLOAD)}</textarea>
        <div class="actions">
          <button id="renderButton" type="button">Render Health Table</button>
          <span class="hint">This submits the JSON to <code>/health-report/render</code> and shows the HTML report below.</span>
        </div>
      </div>
    </section>
    <section class="panel">
      <iframe id="reportFrame" title="Health report output"></iframe>
    </section>
  </main>
  <script>
    const payloadEl = document.getElementById("payload");
    const buttonEl = document.getElementById("renderButton");
    const errorEl = document.getElementById("error");
    const frameEl = document.getElementById("reportFrame");

    async function renderReport() {{
      errorEl.style.display = "none";
      errorEl.textContent = "";

      let parsed;
      try {{
        parsed = JSON.parse(payloadEl.value);
      }} catch (error) {{
        errorEl.style.display = "block";
        errorEl.textContent = `Invalid JSON: ${{error.message}}`;
        return;
      }}

      const response = await fetch("/health-report/render", {{
        method: "POST",
        headers: {{
          "Content-Type": "application/json"
        }},
        body: JSON.stringify(parsed)
      }});

      const responseText = await response.text();
      if (!response.ok) {{
        errorEl.style.display = "block";
        errorEl.textContent = responseText;
        return;
      }}

      frameEl.srcdoc = responseText;
    }}

    buttonEl.addEventListener("click", renderReport);
  </script>
</body>
</html>"""


def render_health_report_html(response: HealthEvaluationResponse) -> str:
    """Render a browser-friendly health report table."""
    rows = []
    for row in response.summary_table:
        dependencies = ", ".join(row.dependencies) if row.dependencies else "none"
        rows.append(
            "<tr>"
            f"<td>{escape(row.component)}</td>"
            f"<td>{escape(row.own_status)}</td>"
            f"<td>{escape(row.effective_status)}</td>"
            f"<td>{escape(dependencies)}</td>"
            f"<td>{escape(row.reason)}</td>"
            "</tr>"
        )

    bfs_order = " -> ".join(response.bfs_traversal_order)
    overall_status = escape(response.overall_status)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DAG Health Evaluation</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5f1e8;
      --surface: #fffdf8;
      --ink: #1e1b16;
      --muted: #6a6257;
      --border: #d9cfbf;
      --accent: #8f3b2e;
    }}
    body {{
      margin: 0;
      padding: 32px;
      background: linear-gradient(180deg, #efe7d7 0%, var(--bg) 100%);
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
    }}
    .shell {{
      max-width: 1080px;
      margin: 0 auto;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 18px;
      box-shadow: 0 18px 60px rgba(41, 31, 20, 0.08);
      overflow: hidden;
    }}
    .header {{
      padding: 28px 32px 18px;
      border-bottom: 1px solid var(--border);
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: 32px;
      line-height: 1.1;
    }}
    .meta {{
      margin: 0;
      color: var(--muted);
      font-size: 16px;
    }}
    .status {{
      display: inline-block;
      margin-top: 14px;
      padding: 8px 12px;
      border-radius: 999px;
      background: #f6ded9;
      color: var(--accent);
      font-weight: 700;
      letter-spacing: 0.02em;
      text-transform: uppercase;
      font-size: 12px;
    }}
    .table-wrap {{
      padding: 22px 26px 30px;
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 15px;
    }}
    th, td {{
      text-align: left;
      padding: 14px 12px;
      border-bottom: 1px solid var(--border);
      vertical-align: top;
    }}
    th {{
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--muted);
      background: #fbf6ed;
    }}
    tr:last-child td {{
      border-bottom: none;
    }}
    code {{
      font-family: Consolas, "Courier New", monospace;
      font-size: 14px;
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="header">
      <h1>System Health Summary</h1>
      <p class="meta"><strong>BFS Traversal:</strong> <code>{escape(bfs_order)}</code></p>
      <div class="status">Overall Status: {overall_status}</div>
    </section>
    <section class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Component</th>
            <th>Own Status</th>
            <th>Effective Status</th>
            <th>Dependencies</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rows)}
        </tbody>
      </table>
    </section>
  </main>
</body>
</html>"""
