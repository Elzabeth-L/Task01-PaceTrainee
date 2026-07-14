"""Lambda entry point for the serverless landing page."""

from html import escape


def _page(request_id: str) -> str:
    safe_request_id = escape(request_id)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="A tiny serverless Python landing page on AWS.">
  <title>Orbit — Serverless by design</title>
  <style>
    :root {{ color-scheme: dark; --ink:#f8fafc; --muted:#a5b4c8; --violet:#8b5cf6; --cyan:#22d3ee; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; min-height:100vh; color:var(--ink); font:16px/1.6 Inter,ui-sans-serif,system-ui,sans-serif;
      background:radial-gradient(circle at 15% 15%,#312e81 0,transparent 32%),radial-gradient(circle at 85% 80%,#164e63 0,transparent 30%),#070b18; }}
    .shell {{ width:min(1120px,92%); margin:auto; }}
    nav {{ display:flex; justify-content:space-between; align-items:center; padding:28px 0; }}
    .brand {{ display:flex; align-items:center; gap:10px; font-weight:800; letter-spacing:.08em; }}
    .orb {{ width:26px; height:26px; border:2px solid var(--cyan); border-radius:50%; box-shadow:0 0 24px var(--cyan); }}
    .pill {{ padding:8px 14px; border:1px solid #ffffff26; border-radius:99px; color:var(--muted); font-size:.85rem; }}
    main {{ min-height:calc(100vh - 160px); display:grid; place-items:center; padding:54px 0 90px; text-align:center; }}
    .hero {{ max-width:850px; }}
    .eyebrow {{ color:var(--cyan); text-transform:uppercase; letter-spacing:.2em; font-weight:700; font-size:.75rem; }}
    h1 {{ margin:18px 0; font-size:clamp(3rem,9vw,7rem); line-height:.94; letter-spacing:-.065em; }}
    h1 span {{ color:transparent; background:linear-gradient(90deg,var(--violet),var(--cyan)); background-clip:text; }}
    .lead {{ max-width:650px; margin:24px auto 36px; color:var(--muted); font-size:clamp(1rem,2.2vw,1.25rem); }}
    .cards {{ display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-top:64px; text-align:left; }}
    .card {{ padding:24px; border:1px solid #ffffff1f; border-radius:20px; background:#ffffff0b; backdrop-filter:blur(12px); }}
    .card b {{ display:block; margin-bottom:6px; }} .card span {{ color:var(--muted); font-size:.9rem; }}
    footer {{ padding:24px 0; color:#64748b; font-size:.72rem; text-align:center; }}
    @media (max-width:680px) {{ .cards {{ grid-template-columns:1fr; }} h1 {{ letter-spacing:-.045em; }} }}
  </style>
</head>
<body>
  <div class="shell">
    <nav><div class="brand"><i class="orb"></i> ORBIT</div><div class="pill">AWS · PYTHON · TERRAFORM</div></nav>
    <main><section class="hero">
      <div class="eyebrow">Small footprint · Big horizon</div>
      <h1>Ship ideas at <span>light speed.</span></h1>
      <p class="lead">A zero-database, serverless landing page powered by Python, AWS Lambda, and API Gateway. Repeatable infrastructure, delivered as code.</p>
      <div class="cards">
        <article class="card"><b>⚡ Serverless</b><span>Scale on demand and pay only when requests arrive.</span></article>
        <article class="card"><b>◈ Reproducible</b><span>Every cloud resource is described and reviewed in Terraform.</span></article>
        <article class="card"><b>✓ Automated</b><span>GitHub Actions plans changes and safely deploys main.</span></article>
      </div>
    </section></main>
    <footer>Request {safe_request_id} · Built without servers to manage</footer>
  </div>
</body>
</html>"""


def lambda_handler(event, context):
    """Return the landing page using the API Gateway payload v2 response shape."""
    request_id = getattr(context, "aws_request_id", "local-preview")
    return {
        "statusCode": 200,
        "headers": {
            "content-type": "text/html; charset=utf-8",
            "cache-control": "public, max-age=300",
            "x-content-type-options": "nosniff",
            "content-security-policy": "default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; frame-ancestors 'none'",
        },
        "body": _page(request_id),
    }
