#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs" / "assets" / "drive-operator-demo.gif"
WIDTH = 960
HEIGHT = 540


def find_chrome() -> str:
    configured = os.environ.get("CHROME_BIN")
    if configured:
        return configured

    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    raise SystemExit("Chrome/Chromium renderer not found. Set CHROME_BIN to generate the GIF.")


def find_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg not found. Install ffmpeg to generate the GIF.")
    return ffmpeg


def run_offer_demo() -> dict[str, object]:
    python_bin = os.environ.get("PYTHON_BIN", sys.executable)
    result = subprocess.run(
        [python_bin, "scripts/run_offer_demo.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def short(value: object, limit: int = 74) -> str:
    text = str(value)
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def slide_html(title: str, eyebrow: str, bullets: list[str], proof: str, step: str) -> str:
    items = "\n".join(f"<li>{html.escape(item)}</li>" for item in bullets)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      width: {WIDTH}px;
      height: {HEIGHT}px;
      background: #f6f7f9;
      color: #18202a;
      font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
      overflow: hidden;
    }}
    .frame {{
      position: relative;
      width: {WIDTH}px;
      height: {HEIGHT}px;
      padding: 44px 54px;
      background:
        linear-gradient(135deg, rgba(15, 118, 110, 0.12), rgba(29, 78, 216, 0.08) 42%, rgba(255,255,255,0) 64%),
        #f6f7f9;
    }}
    .top {{
      display: flex;
      justify-content: space-between;
      gap: 20px;
      align-items: center;
      margin-bottom: 26px;
    }}
    .eyebrow {{
      color: #0f766e;
      font-size: 19px;
      font-weight: 800;
      letter-spacing: 0;
      text-transform: uppercase;
    }}
    .step {{
      color: #52616f;
      font-size: 17px;
      font-weight: 800;
      padding: 8px 12px;
      border: 1px solid #d8e0e7;
      border-radius: 999px;
      background: #ffffff;
    }}
    h1 {{
      margin: 0 0 20px;
      max-width: 820px;
      color: #18202a;
      font-size: 46px;
      line-height: 1.03;
      letter-spacing: 0;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1.3fr 0.7fr;
      gap: 18px;
      align-items: stretch;
    }}
    .panel {{
      min-height: 232px;
      background: rgba(255,255,255,0.94);
      border: 1px solid #d8e0e7;
      border-radius: 8px;
      box-shadow: 0 18px 38px rgba(24, 32, 42, 0.10);
      padding: 21px 25px;
    }}
    ul {{
      margin: 0;
      padding-left: 24px;
      font-size: 25px;
      line-height: 1.25;
      font-weight: 650;
    }}
    li {{ margin: 0 0 12px; }}
    .proof-label {{
      color: #52616f;
      font-size: 18px;
      font-weight: 800;
      text-transform: uppercase;
      margin-bottom: 13px;
    }}
    .proof {{
      color: #0b4f4a;
      font-size: 28px;
      line-height: 1.14;
      font-weight: 850;
    }}
  </style>
</head>
<body>
  <main class="frame">
    <div class="top">
      <div class="eyebrow">{html.escape(eyebrow)}</div>
      <div class="step">{html.escape(step)}</div>
    </div>
    <h1>{html.escape(title)}</h1>
    <section class="grid">
      <div class="panel">
        <ul>{items}</ul>
      </div>
      <div class="panel">
        <div class="proof-label">Visible proof</div>
        <div class="proof">{html.escape(proof)}</div>
      </div>
    </section>
  </main>
</body>
</html>
"""


def build_slides(payload: dict[str, object]) -> list[str]:
    rag = payload["rag_quality"]  # type: ignore[index]
    analysis = payload["call_analysis"]  # type: ignore[index]
    privacy = payload["privacy"]  # type: ignore[index]
    approval = payload["approval"]  # type: ignore[index]
    crm = payload["crm_handoff"]  # type: ignore[index]
    bitrix = payload["bitrix24_dispatch"]  # type: ignore[index]
    transcription = payload["transcription"]  # type: ignore[index]

    return [
        slide_html(
            "Transcript -> RAG -> approval -> CRM-safe handoff.",
            "2-minute public demo",
            [
                "One reproducible workflow from business input to system handoff.",
                "n8n can orchestrate; backend owns state, quality, audit, and contracts.",
                "Public mode stays dry-run and secret-free.",
            ],
            "Run: python3 scripts/run_offer_demo.py",
            "Frame 1/6",
        ),
        slide_html(
            "Knowledge intake and RAG quality are checked first.",
            "RAG and citations",
            [
                "Google Drive playbook imported into the RAG store.",
                f"RAG eval passed {rag['passed']}/{rag['total']} with citations.",
                "Expected source and required terms are verified before trusting output.",
            ],
            f"rag_quality.ok={rag['ok']}",
            "Frame 2/6",
        ),
        slide_html(
            "Call transcript becomes structured business action.",
            "Call analysis",
            [
                f"Transcription boundary: {transcription['provider']} / {transcription['status']}.",
                f"Lead score: {analysis['score']}/100; risk: {analysis['risk_level']}.",
                f"Next action: {short(analysis['next_action'])}",
            ],
            "JSON summary, objections, risk, next step",
            "Frame 3/6",
        ),
        slide_html(
            "Privacy and human approval stay explicit.",
            "Safe review boundary",
            [
                f"PII redacted before RAG/approval/CRM: {privacy['redacted']}.",
                f"Approval state: {approval['status']} by {approval['reviewer']}.",
                "Telegram payload and callback contract are visible in dry-run mode.",
            ],
            "approval before CRM handoff",
            "Frame 4/6",
        ),
        slide_html(
            "CRM handoff is queued with retryable outbox state.",
            "Integration contract",
            [
                f"CRM handoff status: {crm['status']}.",
                f"Bitrix24 dispatch: {bitrix['method']} / {bitrix['status']}.",
                "Idempotency key, attempts, retry timing, and dead-letter state are modeled.",
            ],
            "Bitrix24 write stays dry-run until enabled",
            "Frame 5/6",
        ),
        slide_html(
            "The hiring signal is production-minded ownership.",
            "What this proves",
            [
                "Backend owns records, RAG, approvals, audit, retries, and contracts.",
                "Workflow output is testable, logged, documented, and handoff-ready.",
                "The same proof is covered by CI and public verification gates.",
            ],
            "49 tests + public verification gate",
            "Frame 6/6",
        ),
    ]


def render_frames(chrome: str, slides: list[str], frame_dir: Path) -> None:
    for index, content in enumerate(slides):
        html_path = frame_dir / f"frame-{index:02d}.html"
        png_path = frame_dir / f"frame-{index:02d}.png"
        html_path.write_text(content, encoding="utf-8")
        subprocess.run(
            [
                chrome,
                "--headless",
                "--disable-gpu",
                "--hide-scrollbars",
                f"--screenshot={png_path}",
                f"--window-size={WIDTH},{HEIGHT}",
                f"file://{html_path}",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not png_path.exists():
            raise SystemExit(f"Chrome did not create {png_path}")


def render_gif(ffmpeg: str, frame_dir: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-framerate",
            "0.65",
            "-i",
            str(frame_dir / "frame-%02d.png"),
            "-vf",
            "fps=10,scale=960:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer:bayer_scale=3",
            "-loop",
            "0",
            str(output),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    data = output.read_bytes()
    if not data.startswith((b"GIF87a", b"GIF89a")):
        raise SystemExit(f"{output} is not a GIF")
    if len(data) < 80_000:
        raise SystemExit(f"{output} is unexpectedly small")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the public DriveDesk AI Operator demo GIF.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    chrome = find_chrome()
    ffmpeg = find_ffmpeg()
    payload = run_offer_demo()
    slides = build_slides(payload)
    with tempfile.TemporaryDirectory(prefix="aiops-demo-gif-") as temp:
        frame_dir = Path(temp)
        render_frames(chrome, slides, frame_dir)
        render_gif(ffmpeg, frame_dir, args.output)
    print(f"wrote {args.output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
