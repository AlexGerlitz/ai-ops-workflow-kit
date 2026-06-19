DEMO_PAGE_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Sales Ops Control Tower</title>
  <link rel="icon" href="data:,">
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #1d232b;
      --muted: #697586;
      --line: #d9dee7;
      --accent: #1167e8;
      --ok: #0b7a45;
      --warn: #a15c00;
      --shadow: 0 16px 40px rgba(19, 35, 61, 0.10);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 15px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .shell { max-width: 1180px; margin: 0 auto; padding: 28px 20px 40px; }
    header {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 18px;
      align-items: end;
      margin-bottom: 20px;
    }
    h1 { margin: 0 0 6px; font-size: clamp(28px, 4vw, 46px); line-height: 1.04; letter-spacing: 0; }
    .subtitle { color: var(--muted); max-width: 760px; margin: 0; }
    button {
      appearance: none;
      border: 0;
      border-radius: 8px;
      background: var(--accent);
      color: white;
      font-weight: 700;
      min-height: 44px;
      padding: 0 18px;
      cursor: pointer;
      box-shadow: var(--shadow);
    }
    button:disabled { cursor: wait; opacity: 0.72; }
    button.secondary {
      background: #27364a;
      box-shadow: none;
    }
    input, select {
      width: 100%;
      min-height: 42px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #ffffff;
      color: var(--text);
      padding: 8px 10px;
      font: inherit;
    }
    input[type="file"] { padding: 8px; }
    label {
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      margin-bottom: 5px;
      text-transform: uppercase;
    }
    .grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 14px; }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      padding: 16px;
      min-width: 0;
    }
    .span-2 { grid-column: span 2; }
    .span-3 { grid-column: span 3; }
    .span-4 { grid-column: span 4; }
    .span-5 { grid-column: span 5; }
    .span-7 { grid-column: span 7; }
    .span-12 { grid-column: span 12; }
    .label { color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; }
    .value { font-size: 28px; font-weight: 800; margin-top: 8px; word-break: break-word; }
    .small { color: var(--muted); font-size: 13px; margin-top: 8px; overflow-wrap: anywhere; }
    .ok { color: var(--ok); }
    .warn { color: var(--warn); }
    .row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
    .metrics {
      grid-column: span 12;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 14px;
      align-items: stretch;
    }
    .metrics .panel { min-height: 128px; }
    .metrics .value { font-size: 24px; }
    .pill {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 9px;
      background: #f9fafb;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }
    pre {
      margin: 10px 0 0;
      padding: 12px;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #0f1720;
      color: #e6edf3;
      min-height: 180px;
      max-height: 460px;
    }
    .stack { display: grid; gap: 10px; }
    .form-grid {
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 10px;
      align-items: end;
      margin-top: 12px;
    }
    .field { grid-column: span 3; min-width: 0; }
    .field.wide { grid-column: span 6; }
    .field.actions {
      grid-column: span 12;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }
    .step {
      display: grid;
      grid-template-columns: 26px 1fr;
      gap: 10px;
      align-items: start;
    }
    .num {
      width: 26px;
      height: 26px;
      border-radius: 50%;
      background: #e8f1ff;
      color: var(--accent);
      display: grid;
      place-items: center;
      font-weight: 800;
    }
    @media (max-width: 840px) {
      header { grid-template-columns: 1fr; align-items: start; }
      .span-2, .span-3, .span-4, .span-5, .span-7 { grid-column: span 12; }
      .field, .field.wide { grid-column: span 12; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <header>
      <div>
        <h1>AI Sales Ops Control Tower</h1>
        <p class="subtitle">Document/CRM knowledge intake, call audio transcription, RAG-backed transcript analysis, OpenAI/Claude/Gemini provider boundary, Telegram callback approval, idempotent Bitrix24 outbox drain, and worker-visible CRM handoff in one reproducible workflow.</p>
      </div>
      <button id="run">Run demo workflow</button>
    </header>

    <section class="grid">
      <div class="metrics">
        <div class="panel">
          <div class="label">Runtime</div>
          <div id="runtime" class="value">Ready</div>
          <div id="runtime-sub" class="small">Waiting for demo run</div>
        </div>
        <div class="panel">
          <div class="label">LLM</div>
          <div id="llm" class="value">--</div>
          <div id="llm-sub" class="small">Provider boundary pending</div>
        </div>
        <div class="panel">
          <div class="label">Transcription</div>
          <div id="transcription" class="value">--</div>
          <div id="transcription-sub" class="small">Call audio transcription pending</div>
        </div>
        <div class="panel">
          <div class="label">Lead score</div>
          <div id="score" class="value">--</div>
          <div id="risk" class="small">Risk level pending</div>
        </div>
        <div class="panel">
          <div class="label">Approval</div>
          <div id="approval" class="value">--</div>
          <div id="reviewer" class="small">Reviewer pending</div>
        </div>
        <div class="panel">
          <div class="label">CRM handoff</div>
          <div id="crm" class="value">--</div>
          <div id="crm-sub" class="small">Bitrix24 dispatch pending</div>
        </div>
        <div class="panel">
          <div class="label">Outbox drain</div>
          <div id="outbox" class="value">--</div>
          <div id="outbox-sub" class="small">Dry-run drain pending</div>
        </div>
        <div class="panel">
          <div class="label">Worker state</div>
          <div id="worker" class="value">--</div>
          <div id="worker-sub" class="small">Runtime not checked</div>
        </div>
      </div>

      <div class="panel span-7">
        <div class="row">
          <span class="pill">Document/CRM intake</span>
          <span class="pill">Call audio transcription</span>
          <span class="pill">OpenAI/Claude/Gemini</span>
          <span class="pill">Transcript</span>
          <span class="pill">RAG</span>
          <span class="pill">Approval</span>
          <span class="pill">Outbox</span>
          <span class="pill">Bitrix24</span>
          <span class="pill">Worker state</span>
        </div>
        <div class="stack" style="margin-top: 16px;">
          <div class="step" data-endpoint="/integrations/google-drive/import"><div class="num">1</div><div><b>Import knowledge playbook</b><div class="small" id="step1">Not run yet</div></div></div>
          <div class="step"><div class="num">2</div><div><b>Transcribe call audio</b><div class="small" id="step2">Not run yet</div></div></div>
          <div class="step"><div class="num">3</div><div><b>Analyze transcript</b><div class="small" id="step3">Not run yet</div></div></div>
          <div class="step"><div class="num">4</div><div><b>Build approval payload</b><div class="small" id="step4">Not run yet</div></div></div>
          <div class="step"><div class="num">5</div><div><b>Queue and drain Bitrix24 handoff</b><div class="small" id="step5">Not run yet</div></div></div>
        </div>
      </div>
      <div class="panel span-5">
        <div class="label">Integration readiness</div>
        <div id="integrations" class="stack" style="margin-top: 12px;"></div>
      </div>
      <div class="panel span-12">
        <div class="row">
          <span class="pill">Live Deepgram</span>
          <span class="pill">Audio upload</span>
          <span class="pill">AI score</span>
          <span class="pill">Approval handoff</span>
        </div>
        <form id="audio-upload-form" class="form-grid">
          <div class="field wide">
            <label for="upload-file">Call recording</label>
            <input id="upload-file" name="file" type="file" accept=".aac,.m4a,.mp3,.mp4,.ogg,.opus,.wav,.webm,audio/*" required>
          </div>
          <div class="field">
            <label for="upload-call-id">Call ID</label>
            <input id="upload-call-id" name="call_id" value="manual-demo-call">
          </div>
          <div class="field">
            <label for="upload-customer-id">Customer ID</label>
            <input id="upload-customer-id" name="customer_id" value="manual-demo-lead">
          </div>
          <div class="field">
            <label for="upload-language">Language</label>
            <select id="upload-language" name="language">
              <option value="ru" selected>ru</option>
              <option value="en">en</option>
            </select>
          </div>
          <div class="field">
            <label for="upload-provider">Provider</label>
            <select id="upload-provider" name="provider">
              <option value="deepgram" selected>deepgram</option>
              <option value="openai_whisper">openai_whisper</option>
            </select>
          </div>
          <div class="field actions">
            <button id="upload-run" type="submit">Transcribe uploaded call</button>
            <button id="upload-approve" class="secondary" type="button" disabled>Approve and drain CRM</button>
            <span id="upload-status" class="small">Waiting for audio</span>
          </div>
        </form>
        <pre id="upload-transcript">{ "transcript": "waiting" }</pre>
      </div>
      <div class="panel span-12">
        <div class="label">Workflow output</div>
        <pre id="output">{ "status": "idle" }</pre>
      </div>
    </section>
  </main>

  <script>
    const runButton = document.getElementById("run");
    const output = document.getElementById("output");
    const uploadForm = document.getElementById("audio-upload-form");
    const uploadButton = document.getElementById("upload-run");
    const uploadApproveButton = document.getElementById("upload-approve");
    const uploadTranscript = document.getElementById("upload-transcript");
    let latestUploadApprovalId = null;
    let latestUploadResult = null;

    const setText = (id, value) => { document.getElementById(id).textContent = value; };
    const pretty = (value) => JSON.stringify(value, null, 2);

    function renderWorkerState(runtime) {
      const worker = runtime.workers.bitrix24_outbox;
      setText("worker", worker.active ? "active" : "off");
      setText("worker-sub", worker.dry_run ? "Public dry-run keeps worker disabled" : `Interval ${worker.interval_seconds}s`);
    }

    function renderLlmState(runtime) {
      const llm = runtime.llm;
      setText("llm", llm.selected_provider);
      setText("llm-sub", llm.supported_providers.join(" / "));
    }

    function renderTranscriptionState(runtime) {
      const transcription = runtime.transcription;
      const deepgram = transcription.providers.find((item) => item.provider === "deepgram");
      setText("transcription", transcription.selected_provider);
      setText("transcription-sub", `Deepgram ${deepgram && deepgram.configured ? "configured" : "not configured"}`);
    }

    function renderIntegrations(runtime) {
      const target = document.getElementById("integrations");
      target.innerHTML = "";
      runtime.capabilities.forEach((item) => {
        const row = document.createElement("div");
        row.className = "row";
        row.innerHTML = `
          <span class="pill">${item.adapter_key}</span>
          <span class="pill ${item.configured ? "ok" : "warn"}">${item.configured ? "configured" : "not configured"}</span>
          <span class="pill ${item.dry_run ? "warn" : "ok"}">${item.dry_run ? "dry run" : "live"}</span>
        `;
        target.appendChild(row);
      });
    }

    async function loadRuntime() {
      const runtimeResponse = await fetch("/runtime");
      const runtimeState = await runtimeResponse.json();
      renderLlmState(runtimeState);
      renderTranscriptionState(runtimeState);
      renderWorkerState(runtimeState);
      const response = await fetch("/integrations/runtime");
      const runtime = await response.json();
      renderIntegrations(runtime);
      setText("runtime-sub", runtime.public_base_url);
    }

    async function runDemo() {
      runButton.disabled = true;
      runButton.textContent = "Running...";
      output.textContent = pretty({ status: "running" });
      try {
        const response = await fetch("/demo/run", { method: "POST" });
        const data = await response.json();
        if (!response.ok) throw new Error(pretty(data));
        const drainResponse = await fetch("/integrations/bitrix24/drain?limit=100", { method: "POST" });
        const drain = await drainResponse.json();
        if (!drainResponse.ok) throw new Error(pretty(drain));
        const runtimeResponse = await fetch("/runtime");
        const runtimeState = await runtimeResponse.json();

        setText("runtime", data.runtime.storage);
        setText("runtime-sub", data.integrations.public_base_url);
        renderLlmState(runtimeState);
        setText("transcription", data.transcription.status);
        setText("transcription-sub", `${data.transcription.provider}: ${data.transcription.segments.length} segment(s)`);
        setText("score", `${data.call_analysis.score}/100`);
        setText("risk", `Risk: ${data.call_analysis.risk_level}`);
        setText("approval", data.approval.status);
        setText("reviewer", data.approval.reviewer);
        setText("crm", data.crm_handoff.status);
        setText("crm-sub", `${data.bitrix24_dispatch.method} / ${data.bitrix24_dispatch.status}`);
        setText("step1", `${data.google_drive_import.source}: ${data.ingestion.chunks} chunk(s), ${data.rag_context_sources.length} source(s) retrieved`);
        setText("step2", `${data.transcription.provider} ${data.transcription.status}: ${data.transcription.segments.length} segment(s)`);
        setText("step3", `${data.call_analysis.next_action}`);
        setText("step4", `${data.telegram_approval.adapter_key} ${data.telegram_approval.status}`);
        setText("outbox", `${drain.dry_run}`);
        setText("outbox-sub", `${drain.dispatched} event(s), ${drain.dead_letter} dead-letter`);
        setText("step5", `${data.crm_handoff.operation} -> ${data.bitrix24_dispatch.status}; drain dry-run: ${drain.dry_run} event(s)`);
        renderWorkerState(runtimeState);
        renderIntegrations(data.integrations);
        output.textContent = pretty({ workflow: data, bitrix24_outbox_drain: drain, runtime: runtimeState });
      } catch (error) {
        output.textContent = pretty({ status: "failed", detail: String(error.message || error) });
      } finally {
        runButton.disabled = false;
        runButton.textContent = "Run demo workflow";
      }
    }

    function renderUploadResult(data) {
      latestUploadResult = data;
      latestUploadApprovalId = data.transcript_result.approval.id;
      const segments = data.transcription.segments || [];
      setText("upload-status", `${data.upload.filename}: ${data.transcription.status}`);
      setText("transcription", data.transcription.status);
      setText("transcription-sub", `${data.transcription.provider}: ${segments.length} segment(s)`);
      setText("score", `${data.transcript_result.score}/100`);
      setText("risk", `Risk: ${data.transcript_result.analysis.risk_level}`);
      setText("approval", data.transcript_result.approval.status);
      setText("reviewer", "waiting for approval");
      setText("crm", "pending");
      setText("crm-sub", "approval required");
      setText("step2", `${data.transcription.provider} ${data.transcription.status}: ${segments.length} segment(s)`);
      setText("step3", data.transcript_result.analysis.next_action);
      setText("step4", `${data.telegram_approval.adapter_key} ${data.telegram_approval.status}`);
      uploadApproveButton.disabled = false;
      uploadTranscript.textContent = data.transcription.transcript || "(empty transcript)";
      output.textContent = pretty({ audio_upload: data });
    }

    async function uploadAudio(event) {
      event.preventDefault();
      uploadButton.disabled = true;
      uploadApproveButton.disabled = true;
      latestUploadApprovalId = null;
      setText("upload-status", "Transcribing...");
      uploadTranscript.textContent = pretty({ status: "transcribing" });
      try {
        const response = await fetch("/demo/audio/upload", {
          method: "POST",
          body: new FormData(uploadForm),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(pretty(data));
        renderUploadResult(data);
      } catch (error) {
        setText("upload-status", "Upload failed");
        uploadTranscript.textContent = pretty({ status: "failed", detail: String(error.message || error) });
      } finally {
        uploadButton.disabled = false;
      }
    }

    async function approveUploadedCall() {
      if (!latestUploadApprovalId) return;
      uploadApproveButton.disabled = true;
      setText("upload-status", "Approving...");
      try {
        const approvalResponse = await fetch(`/approvals/${latestUploadApprovalId}/approve`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ reviewer: "browser-demo", notes: "Approved from live audio upload demo" }),
        });
        const approval = await approvalResponse.json();
        if (!approvalResponse.ok) throw new Error(pretty(approval));
        const drainResponse = await fetch("/integrations/bitrix24/drain?limit=100", { method: "POST" });
        const drain = await drainResponse.json();
        if (!drainResponse.ok) throw new Error(pretty(drain));
        const runtimeResponse = await fetch("/runtime");
        const runtimeState = await runtimeResponse.json();
        setText("approval", approval.status);
        setText("reviewer", approval.reviewer || "browser-demo");
        setText("crm", "queued");
        setText("crm-sub", `drain dry-run: ${drain.dry_run}`);
        setText("outbox", `${drain.dry_run}`);
        setText("outbox-sub", `${drain.dispatched} event(s), ${drain.dead_letter} dead-letter`);
        renderWorkerState(runtimeState);
        setText("upload-status", "Approved and drained");
        output.textContent = pretty({ audio_upload: latestUploadResult, approval, bitrix24_outbox_drain: drain, runtime: runtimeState });
      } catch (error) {
        setText("upload-status", "Approval failed");
        output.textContent = pretty({ status: "approval-failed", detail: String(error.message || error), audio_upload: latestUploadResult });
        uploadApproveButton.disabled = false;
      }
    }

    runButton.addEventListener("click", runDemo);
    uploadForm.addEventListener("submit", uploadAudio);
    uploadApproveButton.addEventListener("click", approveUploadedCall);
    loadRuntime().catch((error) => {
      output.textContent = pretty({ status: "runtime-check-failed", detail: String(error.message || error) });
    });
  </script>
</body>
</html>
"""
