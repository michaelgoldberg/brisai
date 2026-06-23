<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BrisAI — Thoroughbred Handicapping Intelligence</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    /* ── TOKENS ─────────────────────────────────────────────── */
    :root {
      --navy:      #1B2B4B;
      --navy-deep: #111C33;
      --gold:      #C9952A;
      --gold-lt:   #E8B84B;
      --green:     #2D7A4F;
      --page-bg:   #ECEEF2;
      --card-bg:   #FFFFFF;
      --border:    #D8DCE6;
      --text:      #1A1A2E;
      --muted:     #64697A;
      --danger:    #B53A2F;
      --radius:    6px;
      --mono:      'IBM Plex Mono', monospace;
    }

    /* ── RESET ──────────────────────────────────────────────── */
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html { font-size: 15px; }
    body {
      font-family: 'Inter', sans-serif;
      background: var(--page-bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    /* ── HEADER ─────────────────────────────────────────────── */
    header {
      background: var(--navy);
      padding: 0 2rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 62px;
      border-bottom: 3px solid var(--gold);
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .logo {
      font-family: 'Playfair Display', serif;
      font-size: 1.5rem;
      color: #fff;
      letter-spacing: -0.01em;
    }
    .logo span { color: var(--gold); }
    .badge {
      font-size: 0.7rem;
      font-family: var(--mono);
      color: var(--gold-lt);
      letter-spacing: 0.08em;
      text-transform: uppercase;
      opacity: 0.8;
    }

    /* ── MAIN LAYOUT ────────────────────────────────────────── */
    main {
      flex: 1;
      max-width: 860px;
      width: 100%;
      margin: 2.5rem auto;
      padding: 0 1.5rem 4rem;
    }

    /* ── STEP PANELS ────────────────────────────────────────── */
    .step {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 2rem 2.25rem;
      margin-bottom: 1.25rem;
      display: none;
    }
    .step.active { display: block; }
    .step.done {
      display: block;
      opacity: 0.45;
      pointer-events: none;
    }

    .step-label {
      font-family: var(--mono);
      font-size: 0.7rem;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--gold);
      margin-bottom: 0.35rem;
    }
    .step h2 {
      font-family: 'Playfair Display', serif;
      font-size: 1.3rem;
      color: var(--navy);
      margin-bottom: 1.25rem;
    }

    /* ── FORMS ──────────────────────────────────────────────── */
    .field { margin-bottom: 1rem; }
    label {
      display: block;
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--muted);
      margin-bottom: 0.35rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    input[type="text"], input[type="email"], select {
      width: 100%;
      padding: 0.65rem 0.85rem;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      font-family: 'Inter', sans-serif;
      font-size: 0.95rem;
      color: var(--text);
      background: #FAFBFC;
      transition: border-color 0.15s, box-shadow 0.15s;
      appearance: none;
    }
    input:focus, select:focus {
      outline: none;
      border-color: var(--gold);
      box-shadow: 0 0 0 3px rgba(201,149,42,0.12);
    }
    .row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }

    /* ── BUTTONS ────────────────────────────────────────────── */
    .btn {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.65rem 1.4rem;
      border-radius: var(--radius);
      font-weight: 600;
      font-size: 0.9rem;
      cursor: pointer;
      border: none;
      transition: opacity 0.15s, transform 0.1s;
    }
    .btn:active { transform: scale(0.98); }
    .btn:disabled { opacity: 0.45; cursor: not-allowed; transform: none; }
    .btn-primary {
      background: var(--navy);
      color: #fff;
    }
    .btn-primary:hover:not(:disabled) { background: var(--navy-deep); }
    .btn-gold {
      background: var(--gold);
      color: #fff;
    }
    .btn-gold:hover:not(:disabled) { background: var(--gold-lt); }

    /* ── FILE DROP ZONE ─────────────────────────────────────── */
    .dropzone {
      border: 2px dashed var(--border);
      border-radius: var(--radius);
      padding: 2.5rem 1.5rem;
      text-align: center;
      cursor: pointer;
      transition: border-color 0.15s, background 0.15s;
      margin-bottom: 1rem;
    }
    .dropzone:hover, .dropzone.drag-over {
      border-color: var(--gold);
      background: rgba(201,149,42,0.04);
    }
    .dropzone-icon { font-size: 2rem; margin-bottom: 0.5rem; }
    .dropzone p { color: var(--muted); font-size: 0.9rem; }
    .dropzone strong { color: var(--text); }
    .file-chosen {
      display: none;
      align-items: center;
      gap: 0.75rem;
      padding: 0.75rem 1rem;
      background: #F0F7F4;
      border: 1px solid #B3D9C5;
      border-radius: var(--radius);
      margin-bottom: 1rem;
      font-size: 0.875rem;
      color: var(--green);
      font-weight: 500;
    }
    .file-chosen.show { display: flex; }
    #file-input { display: none; }

    /* ── RACE SELECTOR ──────────────────────────────────────── */
    .race-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.65rem;
      margin-bottom: 1.25rem;
    }
    .race-card {
      padding: 0.85rem 1rem;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      cursor: pointer;
      transition: border-color 0.15s, background 0.15s;
    }
    .race-card:hover { border-color: var(--gold); background: #FFFBF4; }
    .race-card.selected {
      border-color: var(--gold);
      background: #FFFBF4;
      box-shadow: 0 0 0 2px rgba(201,149,42,0.25);
    }
    .race-card-num {
      font-family: var(--mono);
      font-size: 0.75rem;
      color: var(--gold);
      font-weight: 500;
      margin-bottom: 0.15rem;
    }
    .race-card-title {
      font-weight: 600;
      font-size: 0.875rem;
      color: var(--text);
    }
    .race-card-meta {
      font-size: 0.75rem;
      color: var(--muted);
      margin-top: 0.15rem;
    }

    /* ── ANALYSIS OUTPUT ────────────────────────────────────── */
    #analysis-wrap { display: none; }
    #analysis-wrap.show { display: block; }

    .analysis-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 1rem;
      padding-bottom: 0.75rem;
      border-bottom: 2px solid var(--border);
    }
    .analysis-title {
      font-family: 'Playfair Display', serif;
      font-size: 1.1rem;
      color: var(--navy);
    }
    .pulse {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.75rem;
      font-family: var(--mono);
      color: var(--green);
    }
    .pulse-dot {
      width: 7px; height: 7px;
      background: var(--green);
      border-radius: 50%;
      animation: pulse 1.2s ease-in-out infinite;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(0.7); }
    }
    .pulse.hidden { display: none; }

    #analysis-body {
      font-size: 0.9rem;
      line-height: 1.7;
      color: var(--text);
      white-space: pre-wrap;
      font-family: var(--mono);
      background: #F8F9FB;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.5rem;
      min-height: 200px;
      max-height: 72vh;
      overflow-y: auto;
    }

    /* Section header highlighting inside analysis */
    .analysis-section-header {
      color: var(--gold);
      font-weight: 700;
    }

    /* ── HORSE COUNT PILL ───────────────────────────────────── */
    .pill {
      display: inline-block;
      padding: 0.15rem 0.55rem;
      border-radius: 99px;
      font-size: 0.7rem;
      font-family: var(--mono);
      background: #EEF0F4;
      color: var(--muted);
    }

    /* ── ERROR ──────────────────────────────────────────────── */
    .error-msg {
      display: none;
      padding: 0.75rem 1rem;
      background: #FDF2F2;
      border: 1px solid #F5C6C6;
      border-radius: var(--radius);
      color: var(--danger);
      font-size: 0.875rem;
      margin-top: 0.75rem;
    }
    .error-msg.show { display: block; }

    /* ── TRIAL BADGE ────────────────────────────────────────── */
    .trial-badge {
      display: none;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.75rem;
      font-family: var(--mono);
      color: var(--gold);
      background: rgba(201,149,42,0.1);
      border: 1px solid rgba(201,149,42,0.3);
      border-radius: 99px;
      padding: 0.25rem 0.7rem;
    }
    .trial-badge.show { display: flex; }

    /* ── EXPIRED SCREEN ─────────────────────────────────────── */
    #expired-screen {
      display: none;
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 3rem 2.25rem;
      text-align: center;
    }
    #expired-screen.show { display: block; }
    #expired-screen .icon { font-size: 2.5rem; margin-bottom: 1rem; }
    #expired-screen h2 {
      font-family: 'Playfair Display', serif;
      font-size: 1.4rem;
      color: var(--navy);
      margin-bottom: 0.75rem;
    }
    #expired-screen p {
      color: var(--muted);
      max-width: 400px;
      margin: 0 auto 1.5rem;
      line-height: 1.6;
    }
    #expired-screen a {
      color: var(--gold);
      font-weight: 600;
    }

    /* ── FOOTER ─────────────────────────────────────────────── */
    footer {
      text-align: center;
      padding: 1.25rem;
      font-size: 0.75rem;
      color: var(--muted);
      border-top: 1px solid var(--border);
    }

    /* ── RESPONSIVE ─────────────────────────────────────────── */
    @media (max-width: 600px) {
      main { padding: 0 1rem 3rem; }
      .step { padding: 1.5rem 1.25rem; }
      .row-2, .race-grid { grid-template-columns: 1fr; }
      header { padding: 0 1rem; }
    }
  </style>
</head>
<body>

  <header>
    <div class="logo">Bris<span>AI</span></div>
    <div style="display:flex;align-items:center;gap:1rem;">
      <div class="trial-badge" id="trial-badge">⏱ <span id="trial-days-text"></span></div>
      <div class="badge">Powered by Claude</div>
    </div>
  </header>

  <main>

    <!-- EXPIRED SCREEN -->
    <div id="expired-screen">
      <div class="icon">🔒</div>
      <h2>Your trial has ended</h2>
      <p id="expired-msg">Your 3-day trial period is complete. Get in touch to unlock full access.</p>
      <a href="mailto:mgoldberg@emarketingsg.com">Contact us to continue →</a>
    </div>

    <!-- STEP 1: Contact -->
    <div class="step active" id="step-1">
      <div class="step-label">Step 1 of 3</div>
      <h2>Tell us who you are</h2>
      <div class="row-2">
        <div class="field">
          <label for="name">Full Name</label>
          <input type="text" id="name" placeholder="Jane Smith" autocomplete="name">
        </div>
        <div class="field">
          <label for="email">Email Address</label>
          <input type="email" id="email" placeholder="jane@yourtrack.com" autocomplete="email">
        </div>
      </div>
      <div class="field">
        <label for="company">Organization (optional)</label>
        <input type="text" id="company" placeholder="Track, syndicate, or service name">
      </div>
      <button class="btn btn-primary" id="btn-register">Continue →</button>
      <div class="error-msg" id="err-1"></div>
    </div>

    <!-- STEP 2: File Upload -->
    <div class="step" id="step-2">
      <div class="step-label">Step 2 of 3</div>
      <h2>Upload your Brisnet file</h2>

      <div class="dropzone" id="dropzone">
        <div class="dropzone-icon">📋</div>
        <p><strong>Drop your .bris / .DRF file here</strong></p>
        <p>or click to browse</p>
      </div>
      <input type="file" id="file-input" accept=".bris,.DRF,.drf,.csv">
      <div class="file-chosen" id="file-chosen">
        <span>✓</span>
        <span id="file-name"></span>
      </div>

      <button class="btn btn-primary" id="btn-upload" disabled>Parse Race Card →</button>
      <div class="error-msg" id="err-2"></div>
    </div>

    <!-- STEP 3: Race Picker + Analysis -->
    <div class="step" id="step-3">
      <div class="step-label">Step 3 of 3</div>
      <h2>Select a race to analyze</h2>
      <div class="race-grid" id="race-grid"></div>
      <button class="btn btn-gold" id="btn-analyze" disabled>Run AI Analysis →</button>
      <div class="error-msg" id="err-3"></div>
    </div>

    <!-- Analysis Output (appears below step 3) -->
    <div id="analysis-wrap">
      <div class="step active" style="display:block;">
        <div class="analysis-header">
          <div class="analysis-title" id="analysis-title">Handicapping Analysis</div>
          <div class="pulse hidden" id="pulse-indicator">
            <span class="pulse-dot"></span> Analyzing…
          </div>
        </div>
        <div id="analysis-body"></div>
      </div>
    </div>

  </main>

  <footer>BrisAI · Trial Edition · Brisnet data + Claude AI</footer>

  <script>
    // ── STATE ─────────────────────────────────────────────────
    let uploadId      = null;
    let selectedRace  = null;
    let selectedFile  = null;

    // ── HELPERS ───────────────────────────────────────────────
    function showError(el, msg) {
      el.textContent = msg;
      el.classList.add('show');
    }
    function clearError(el) { el.classList.remove('show'); }

    function markDone(stepId) {
      document.getElementById(stepId).classList.remove('active');
      document.getElementById(stepId).classList.add('done');
    }

    function activateStep(stepId) {
      const el = document.getElementById(stepId);
      el.classList.add('active');
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // ── STEP 1: REGISTER ──────────────────────────────────────
    const btnRegister   = document.getElementById('btn-register');
    const errEl1        = document.getElementById('err-1');
    const trialBadge    = document.getElementById('trial-badge');
    const trialDaysText = document.getElementById('trial-days-text');
    const expiredScreen = document.getElementById('expired-screen');
    const expiredMsg    = document.getElementById('expired-msg');

    btnRegister.addEventListener('click', async () => {
      clearError(errEl1);
      const name    = document.getElementById('name').value.trim();
      const email   = document.getElementById('email').value.trim();
      const company = document.getElementById('company').value.trim();

      if (!name || !email) {
        showError(errEl1, 'Please enter your name and email address.'); return;
      }

      btnRegister.disabled = true;
      btnRegister.textContent = 'Checking…';

      try {
        const res  = await fetch('/register', {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ name, email, company }),
        });
        const data = await res.json();

        if (data.trial_expired) {
          // Hide all steps, show expired screen
          document.querySelectorAll('.step').forEach(s => s.style.display = 'none');
          expiredMsg.textContent = data.message;
          expiredScreen.classList.add('show');
          return;
        }

        if (!res.ok) throw new Error(data.error || 'Registration failed.');

        // Show days remaining in header
        const days = data.days_remaining;
        trialDaysText.textContent = `${days} day${days !== 1 ? 's' : ''} left`;
        trialBadge.classList.add('show');

        markDone('step-1');
        activateStep('step-2');
      } catch (e) {
        showError(errEl1, e.message);
        btnRegister.disabled = false;
        btnRegister.textContent = 'Continue →';
      }
    });

    // ── STEP 2: FILE UPLOAD ───────────────────────────────────
    const dropzone  = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');
    const fileChosen= document.getElementById('file-chosen');
    const fileName  = document.getElementById('file-name');
    const btnUpload = document.getElementById('btn-upload');
    const errEl2    = document.getElementById('err-2');

    dropzone.addEventListener('click', () => fileInput.click());

    dropzone.addEventListener('dragover', e => {
      e.preventDefault(); dropzone.classList.add('drag-over');
    });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
    dropzone.addEventListener('drop', e => {
      e.preventDefault();
      dropzone.classList.remove('drag-over');
      if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
    });
    fileInput.addEventListener('change', () => {
      if (fileInput.files[0]) setFile(fileInput.files[0]);
    });

    function setFile(file) {
      selectedFile = file;
      fileName.textContent = file.name;
      fileChosen.classList.add('show');
      btnUpload.disabled = false;
    }

    btnUpload.addEventListener('click', async () => {
      if (!selectedFile) return;
      clearError(errEl2);
      btnUpload.disabled = true;
      btnUpload.textContent = 'Parsing…';

      const form = new FormData();
      form.append('file', selectedFile);

      try {
        const res  = await fetch('/upload', { method: 'POST', body: form });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Upload failed.');

        uploadId = data.upload_id;
        buildRaceGrid(data.races);
        markDone('step-2');
        activateStep('step-3');
      } catch (e) {
        showError(errEl2, e.message);
        btnUpload.disabled = false;
        btnUpload.textContent = 'Parse Race Card →';
      }
    });

    // ── STEP 3: RACE GRID ─────────────────────────────────────
    const raceGrid  = document.getElementById('race-grid');
    const btnAnalyze= document.getElementById('btn-analyze');
    const errEl3    = document.getElementById('err-3');

    function buildRaceGrid(races) {
      raceGrid.innerHTML = '';
      races.forEach(race => {
        const parts = race.key.split('|');
        const raceNum = parts[2];
        const card = document.createElement('div');
        card.className = 'race-card';
        card.dataset.key = race.key;
        card.innerHTML = `
          <div class="race-card-num">RACE ${raceNum}</div>
          <div class="race-card-title">${race.race_class}</div>
          <div class="race-card-meta">
            ${race.surface} · ${race.purse}
            <span class="pill">${race.num_horses} horses</span>
          </div>`;
        card.addEventListener('click', () => selectRace(card, race));
        raceGrid.appendChild(card);
      });
    }

    function selectRace(card, race) {
      document.querySelectorAll('.race-card').forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      selectedRace = race;
      btnAnalyze.disabled = false;

      // Update analysis title
      document.getElementById('analysis-title').textContent =
        `Race ${race.key.split('|')[2]} — ${race.race_class} — ${race.num_horses} horses`;
    }

    // ── ANALYSIS: SSE STREAM ──────────────────────────────────
    const analysisWrap = document.getElementById('analysis-wrap');
    const analysisBody = document.getElementById('analysis-body');
    const pulseEl      = document.getElementById('pulse-indicator');

    btnAnalyze.addEventListener('click', () => {
      if (!selectedRace) return;
      clearError(errEl3);

      analysisBody.textContent = '';
      analysisWrap.classList.add('show');
      pulseEl.classList.remove('hidden');
      btnAnalyze.disabled = true;
      btnAnalyze.textContent = 'Analyzing…';

      analysisWrap.scrollIntoView({ behavior: 'smooth', block: 'start' });

      const url = `/analyze?upload_id=${encodeURIComponent(uploadId)}&race_key=${encodeURIComponent(selectedRace.key)}`;
      const es  = new EventSource(url);

      es.onmessage = (e) => {
        const msg = JSON.parse(e.data);

        if (msg.error) {
          es.close();
          pulseEl.classList.add('hidden');
          if (msg.trial_expired) {
            document.querySelectorAll('.step').forEach(s => s.style.display = 'none');
            document.getElementById('analysis-wrap').style.display = 'none';
            expiredMsg.textContent = 'Your trial has ended. Contact us to continue.';
            expiredScreen.classList.add('show');
            return;
          }
          showError(errEl3, msg.error);
          btnAnalyze.disabled = false;
          btnAnalyze.textContent = 'Run AI Analysis →';
          return;
        }

        if (msg.text) {
          analysisBody.textContent += msg.text;
          analysisBody.scrollTop = analysisBody.scrollHeight;
        }

        if (msg.done) {
          es.close();
          pulseEl.classList.add('hidden');
          btnAnalyze.disabled = false;
          btnAnalyze.textContent = 'Re-run Analysis →';
        }
      };

      es.onerror = () => {
        es.close();
        pulseEl.classList.add('hidden');
        if (!analysisBody.textContent) {
          showError(errEl3, 'Connection lost. Please try again.');
        }
        btnAnalyze.disabled = false;
        btnAnalyze.textContent = 'Run AI Analysis →';
      };
    });
  </script>
</body>
</html>
