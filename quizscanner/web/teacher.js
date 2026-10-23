// Panel nauczyciela. Odpytuje /api/state?full=1 i steruje sesja.
const LETTERS = ["A", "B", "C", "D"];
const $ = id => document.getElementById(id);

function esc(s) {
  return (s || "").replace(/[&<>"]/g, c => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
async function api(path, body) {
  const opt = body ? { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body) } : {};
  return (await fetch(path, opt)).json();
}
const ctl = (action, extra) => api("/api/control", Object.assign({ action }, extra || {}));

// ---- sterowanie quizem ----
$("startBtn").onclick = () => ctl("start");
$("revealBtn").onclick = () => ctl("reveal");
$("nextBtn").onclick = () => ctl("next");
$("prevBtn").onclick = () => ctl("prev");
$("resetBtn").onclick = () => { if (confirm(t("t_confirm_reset"))) ctl("reset"); };
$("speedToggle").onchange = () => ctl("speed_bonus", { value: $("speedToggle").checked });
$("autoToggle").onchange = () => ctl("auto_mode", { value: $("autoToggle").checked });
$("editorBtn").onclick = () => window.open("/editor", "_blank");
$("boardBtn").onclick = () => window.open("/board", "_blank");
$("loadBtn").onclick = async () => {
  const name = $("quizSel").value;
  if (name) await api("/api/load", { name });
  refreshState();
};

// ---- klasy ----
let lastState = null;
async function loadClasses() {
  const r = await api("/api/classes");
  $("classSel").innerHTML = (r.classes || []).map(c =>
    `<option value="${esc(c.id)}" ${c.id === r.active ? "selected" : ""}>👥 ${esc(c.name)} (${c.count})</option>`).join("");
}
$("classSel").onchange = async () => {
  const played = lastState && (lastState.leaderboard || []).length;
  if (played && !confirm(t("cl_confirm_switch"))) { loadClasses(); return; }
  await api("/api/class/select", { id: $("classSel").value, reset: true });
  refreshState();
};

// ---- losowanie ucznia ----
$("drawBtn").onclick = async () => {
  const r = await ctl("draw");
  $("drawOut").innerHTML = r.ok
    ? `🎲 <b>${esc(r.draw.name)}</b> · ${t("dr_left", { n: r.draw.left })}`
    : t("dr_empty");
};
$("speakToggle").onchange = () =>
  api("/api/settings", { speak_draw: $("speakToggle").checked });

// ---- wznowiona gra ----
$("restoreNew").onclick = () => {
  if (confirm(t("t_confirm_reset"))) ctl("reset").then(refreshState);
};
$("restoreOk").onclick = () => ctl("dismiss_restore").then(refreshState);

// ---- pilot w telefonie ----
async function showPair() {
  const ip = $("pairIp").value;
  const r = await api("/api/pair" + (ip ? "?ip=" + encodeURIComponent(ip) : ""));
  $("pairQr").src = "/api/pair.png?ip=" + encodeURIComponent(r.ip) + "&t=" + Date.now();
  $("pairUrl").textContent = r.url;
  $("pairIp").innerHTML = r.ips.map(a =>
    `<option ${a === r.ip ? "selected" : ""}>${esc(a)}</option>`).join("");
  $("pairIpRow").classList.toggle("hidden", r.ips.length < 2);
  $("pairModal").classList.remove("hidden");
}
$("pairBtn").onclick = showPair;
$("pairIp").onchange = showPair;
$("pairClose").onclick = () => $("pairModal").classList.add("hidden");
$("pairModal").onclick = e => {
  if (e.target === $("pairModal")) $("pairModal").classList.add("hidden");
};
$("pairReset").onclick = async () => {
  if (!confirm(t("pr_reset_confirm"))) return;
  await api("/api/pair/reset", {});
  showPair();
};

// ---- ustawienia aplikacji ----
$("langSel").onchange = async () => {
  await api("/api/settings", { lang: $("langSel").value });
  setLang($("langSel").value);
  refreshState();
};
$("themeSel").onchange = async () => {
  setTheme($("themeSel").value);          // od razu widać, bez czekania na serwer
  await api("/api/settings", { theme: $("themeSel").value });
};
$("onlyKnownToggle").onchange = () =>
  api("/api/settings", { only_known: $("onlyKnownToggle").checked });
$("soundToggle").onchange = () =>
  api("/api/settings", { sound: $("soundToggle").checked });
$("volume").oninput = () => { $("volVal").textContent = $("volume").value + "%"; };
$("volume").onchange = () =>
  api("/api/settings", { volume: +$("volume").value / 100 });
$("autoReportToggle").onchange = () =>
  api("/api/settings", { auto_report: $("autoReportToggle").checked });
$("updateToggle").onchange = async () => {
  await api("/api/settings", { check_updates: $("updateToggle").checked });
  checkUpdate();
};
$("camApply").onclick = async () => {
  await api("/api/settings", { camera: $("camSrc").value.trim() || "0" });
  // odśwież strumień podglądu (kamera startuje na nowo)
  setTimeout(() => { $("cam").src = "/video_feed?" + Date.now(); }, 800);
};

// ---- pomoc: telefon jako kamera ----
const PHONE_HELP = {
  pl: {
    title: "Telefon zamiast kamery internetowej",
    body: `
      <ol>
        <li>Zainstaluj w telefonie darmową aplikację streamującą obraz:
          <b>IP Webcam</b> (Android) albo <b>Iriun Webcam</b> / <b>DroidCam</b> (Android i iPhone).</li>
        <li>Podłącz telefon do <b>tej samej sieci Wi-Fi</b> co komputer.</li>
        <li>Uruchom aplikację i wybierz „Start server". Pokaże adres, np.
          <code>http://192.168.1.50:8080</code>.</li>
        <li>Wpisz tutaj adres strumienia i kliknij <b>Przełącz</b>:
          <ul>
            <li>IP Webcam: <code>http://192.168.1.50:8080/video</code></li>
            <li>DroidCam: <code>http://192.168.1.50:4747/video</code></li>
          </ul></li>
        <li>Ustaw telefon tak, by widział całą klasę — najlepiej na statywie
          lub oparty o coś stabilnego.</li>
      </ol>
      <p><b>Wskazówka:</b> Iriun i DroidCam mają też wersję na komputer, która
      tworzy zwykłą „kamerę” w systemie — wtedy zamiast adresu wpisz numer
      <code>1</code> lub <code>2</code>.</p>`,
  },
  en: {
    title: "Phone instead of a webcam",
    body: `
      <ol>
        <li>Install a free streaming app on the phone: <b>IP Webcam</b> (Android)
          or <b>Iriun Webcam</b> / <b>DroidCam</b> (Android and iPhone).</li>
        <li>Connect the phone to the <b>same Wi-Fi network</b> as the computer.</li>
        <li>Open the app and tap “Start server”. It shows an address, e.g.
          <code>http://192.168.1.50:8080</code>.</li>
        <li>Type the stream address here and click <b>Switch</b>:
          <ul>
            <li>IP Webcam: <code>http://192.168.1.50:8080/video</code></li>
            <li>DroidCam: <code>http://192.168.1.50:4747/video</code></li>
          </ul></li>
        <li>Position the phone so it sees the whole class — a tripod or a stable
          support works best.</li>
      </ol>
      <p><b>Tip:</b> Iriun and DroidCam also have desktop clients that create a
      regular system camera — then enter <code>1</code> or <code>2</code> instead
      of an address.</p>`,
  },
};
function showPhoneHelp() {
  const h = PHONE_HELP[document.documentElement.lang] || PHONE_HELP.pl;
  $("phTitle").textContent = h.title;
  $("phBody").innerHTML = h.body;
  $("phoneModal").classList.remove("hidden");
}
$("phoneHelpBtn").onclick = showPhoneHelp;
$("phClose").onclick = () => $("phoneModal").classList.add("hidden");
$("phoneModal").onclick = e => {
  if (e.target === $("phoneModal")) $("phoneModal").classList.add("hidden");
};

// ---- dane startowe ----
async function loadQuizList() {
  const r = await api("/api/quizzes");
  const sel = $("quizSel");
  sel.innerHTML = "";
  (r.quizzes || []).forEach(q => {
    const o = document.createElement("option");
    o.value = q; o.textContent = q;
    if (q === r.active) o.selected = true;
    sel.appendChild(o);
  });
  if (!r.quizzes || !r.quizzes.length)
    sel.innerHTML = `<option value="">${t("t_no_quizzes")}</option>`;
}

async function loadMeta() {
  const m = await api("/api/meta");
  $("lanUrl").innerHTML = `${t("t_lan_board")}: <b>http://${m.lan_ip}:${m.port}/board</b>`;
}

async function loadSettings() {
  const s = await api("/api/settings");
  $("langSel").value = s.lang || "pl";
  $("camSrc").value = s.camera != null ? s.camera : "0";
  $("onlyKnownToggle").checked = !!s.only_known;
  $("soundToggle").checked = s.sound !== false;
  $("volume").value = Math.round((s.volume != null ? s.volume : 0.6) * 100);
  $("volVal").textContent = $("volume").value + "%";
  $("autoReportToggle").checked = s.auto_report !== false;
  $("updateToggle").checked = s.check_updates !== false;
  $("speakToggle").checked = !!s.speak_draw;
}

// ---- raport ----
const REPORT_FORMATS = ["pdf", "xlsx", "csv", "html", "json", "txt"];

function reportRow(st, total) {
  return `<tr><td class="p">${st.place}</td><td>${esc(st.name)}</td>
    <td class="n">#${st.id}</td><td class="n">${st.score}</td>
    <td class="n">${st.correct}/${total}</td><td class="n">${st.percent}%</td></tr>`;
}

function renderReport(r) {
  const s = r.summary;
  if (!s.questions) {
    $("repBody").innerHTML = `<p class="muted">${t("r_empty")}</p>`;
  } else {
    const hardest = s.hardest_n
      ? `<p class="muted">${t("r_hardest")}: <b>${s.hardest_n}.</b> ${tex(s.hardest_text)}
         — ${s.hardest_percent}%</p>` : "";
    $("repBody").innerHTML = `
      <div class="rep-cards">
        <div class="stat"><div class="k">${t("r_stat_students")}</div><div class="v">${s.students}</div></div>
        <div class="stat"><div class="k">${t("r_stat_questions")}</div><div class="v">${s.questions}</div></div>
        <div class="stat"><div class="k">${t("r_stat_avg")}</div><div class="v">${s.avg_percent}%</div></div>
        <div class="stat"><div class="k">${t("r_stat_best")}</div><div class="v sm">${esc(s.best || "—")}</div></div>
      </div>
      ${hardest}
      <table class="students rep-table"><thead><tr>
        <th>${t("r_col_place")}</th><th>${t("r_col_student")}</th><th>${t("t_col_id")}</th>
        <th>${t("r_col_points")}</th><th>${t("r_col_correct")}</th><th>${t("r_col_percent")}</th>
      </tr></thead><tbody>
        ${r.students.map(st => reportRow(st, s.questions)).join("")}
      </tbody></table>`;
  }

  $("repFormats").innerHTML = REPORT_FORMATS.map(f =>
    `<button class="btn-ghost fmt" data-fmt="${f}">${t("r_fmt_" + f)}</button>`).join("");
  $("repFormats").querySelectorAll("button").forEach(b => {
    b.onclick = () => window.open("/api/report?format=" + b.dataset.fmt, "_blank");
  });

  const saved = (r.saved || []).slice(0, 8);
  $("repSaved").innerHTML = `<div class="field">${t("r_open_folder")}</div>
    <code>${esc(r.dir || "")}</code>
    <div class="field mt">${t("r_recent")}</div>` + (saved.length
      ? `<ul class="rep-files">${saved.map(f =>
          `<li>${esc(f.file)} <span class="muted">${Math.round(f.size / 1024)} kB</span></li>`).join("")}</ul>`
      : `<p class="muted">${t("r_no_recent")}</p>`);
}

async function openReport() {
  $("reportModal").classList.remove("hidden");
  $("repBody").innerHTML = "…";
  renderReport(await api("/api/report/preview"));
}

$("reportBtn").onclick = openReport;
$("repClose").onclick = () => $("reportModal").classList.add("hidden");
$("reportModal").onclick = e => {
  if (e.target === $("reportModal")) $("reportModal").classList.add("hidden");
};
$("repSave").onclick = async () => {
  const r = await api("/api/export", {});
  alert(r.ok ? t("r_saved_to") + "\n" + r.paths.join("\n") : t("r_empty"));
  renderReport(await api("/api/report/preview"));
};

// ---- aktualizacje ----
let updateInfo = null;

async function checkUpdate(force) {
  try {
    updateInfo = await api("/api/update" + (force ? "?force=1" : ""));
  } catch (e) { return; }
  const bar = $("updateBar");
  const state = $("updateState");
  if (updateInfo.disabled) { state.textContent = t("u_check_sub"); bar.classList.add("hidden"); return; }
  if (updateInfo.update) {
    $("updateText").textContent = t("u_available", {
      version: updateInfo.latest, current: updateInfo.current });
    $("updateBtn").classList.toggle("hidden", !updateInfo.can_apply);
    bar.classList.remove("hidden");
    state.textContent = t("u_available", {
      version: updateInfo.latest, current: updateInfo.current });
  } else {
    bar.classList.add("hidden");
    state.textContent = updateInfo.error ? t("u_check_sub") : t("u_up_to_date");
  }
}

$("updateClose").onclick = () => $("updateBar").classList.add("hidden");
$("updatePage").onclick = () =>
  window.open((updateInfo && updateInfo.url) || "https://github.com/PiotrKajor/QuizScanner/releases", "_blank");
$("updateBtn").onclick = async () => {
  $("updateText").textContent = t("u_downloading");
  $("updateBtn").disabled = true;
  const r = await api("/api/update/apply", {});
  $("updateBtn").disabled = false;
  if (r.ok) {
    $("updateText").textContent = t("u_ready");
    $("updateBtn").classList.add("hidden");
  } else if (r.error === "source") {
    $("updateText").textContent = t("u_source_hint");
    $("updateBtn").classList.add("hidden");
  } else {
    $("updateText").textContent = t("u_failed");
  }
};

// ---- render ----
function updateCamNote(cameraOk) {
  const el = $("camNote");
  el.textContent = cameraOk ? t("t_cam_hint") : t("t_cam_wait");
  el.style.color = cameraOk ? "" : "var(--bad)";
}

function renderOpts(st) {
  const q = st.question;
  if (!q) { $("opts").innerHTML = ""; return; }
  $("opts").innerHTML = [0, 1, 2, 3].map(i => {
    const L = LETTERS[i];
    const correct = q.correct === i;
    return `<div class="opt-t opt-${L} ${correct ? "correct" : ""}">
      <span class="badge">${L}</span>
      <span class="c">${tex(q.answers[i] || "")}</span>
      <span class="num">${st.distribution[L] || 0}</span>
      ${correct ? '<span class="flag">✓</span>' : ""}
    </div>`;
  }).join("");
}

function renderStudents(st) {
  const students = st.students || {};
  const q = st.question || {};
  const correctL = (q.correct != null) ? LETTERS[q.correct] : null;
  const scores = st.scores || {};
  const rows = Object.keys(students).map(id => {
    const s = students[id];
    const ok = correctL && s.answer === correctL;
    const mark = correctL ? (ok ? '<span class="ans-ok">✓</span>' : '<span class="ans-bad">✗</span>') : "";
    return `<tr>
      <td>#${id}</td><td>${esc(s.name)}</td>
      <td><span class="badge badge-sm badge-${s.answer}">${s.answer}</span> ${mark}</td>
      <td>${scores[id] || 0}</td></tr>`;
  });
  $("studentsBody").innerHTML = rows.length ? rows.join("")
    : `<tr><td colspan="4" style="color:var(--muted)">${t("t_no_answers")}</td></tr>`;
}

function renderLead(st) {
  const lead = st.leaderboard || [];
  $("lead").innerHTML = lead.length ? lead.map((r, i) =>
    `<li><span class="p">${i + 1}</span><span class="n">${esc(r.name)}</span><span class="s">${r.score} pkt</span></li>`
  ).join("") : `<li><span class="n" style="color:var(--muted)">${t("t_no_results")}</span></li>`;
}

const PHASE_KEY = { idle: "idle", question: "question", reveal: "reveal", podium: "podium" };

async function refreshState() {
  let st;
  try { st = await api("/api/state?full=1"); } catch (e) { return; }
  // Urządzenie odłączone przyciskiem „Odłącz wszystkie” — wraca do pilota z instrukcją.
  if (st.error === "locked") { location.href = "/remote"; return; }
  const q = st.question;
  $("counter").textContent = st.total
    ? t("t_question_of", { n: st.index + 1, total: st.total }) : "—";
  lastState = st;
  const ph = $("phase");
  ph.textContent = t("ph_" + st.phase);
  ph.className = "phase " + (PHASE_KEY[st.phase] || "idle");
  $("qtext").innerHTML = q ? tex(q.text) : TeX.esc(t("t_load_quiz_first"));
  $("timeLeft").textContent = st.time_left != null ? Math.ceil(st.time_left) + " s" : "—";
  $("answered").textContent = st.answered;
  const d = st.distribution;
  $("dist").textContent = `${d.A}/${d.B}/${d.C}/${d.D}`;

  if (document.activeElement !== $("speedToggle")) $("speedToggle").checked = !!st.speed_bonus;
  if (document.activeElement !== $("autoToggle")) $("autoToggle").checked = !!st.auto_mode;
  if (document.activeElement !== $("onlyKnownToggle") && st.only_known != null)
    $("onlyKnownToggle").checked = !!st.only_known;

  // Pasek trybu automatycznego + blokada przycisków ręcznych.
  const bar = $("autoBar");
  if (st.auto_mode) {
    bar.classList.remove("hidden");
    bar.textContent = t("t_auto_running") +
      (st.auto_next_in != null ? "  ·  " + Math.ceil(st.auto_next_in) + " s" : "");
  } else {
    bar.classList.add("hidden");
  }
  ["startBtn", "revealBtn", "nextBtn", "prevBtn"].forEach(
    id => { $(id).disabled = !!st.auto_mode; });

  const rb = $("restoreBar");
  rb.classList.toggle("hidden", !st.restored_at);
  if (st.restored_at)
    $("restoreText").textContent = t("rs_restored", {
      time: new Date(st.restored_at * 1000).toLocaleTimeString().slice(0, 5) });

  const missing = st.missing || [];
  $("missing").classList.toggle("hidden", !missing.length);
  $("missing").textContent = missing.length
    ? t("rm_missing", { n: missing.length }) + ": " + missing.map(m => m.name).join(", ") : "";

  renderOpts(st);
  renderStudents(st);
  renderLead(st);
  updateCamNote(st.camera_ok);
}

// Po zmianie języka odśwież teksty zależne od danych.
document.addEventListener("i18n:changed", () => {
  fillThemeSelect($("themeSel"));
  loadQuizList();
  loadClasses();
  loadMeta();
});

(async function init() {
  await initLang();
  fillThemeSelect($("themeSel"));
  $("themeSel").value = document.documentElement.dataset.theme || "dark";
  await loadSettings();
  $("langSel").value = document.documentElement.lang;
  loadQuizList();
  loadClasses();
  loadMeta();
  refreshState();
  checkUpdate();
  setInterval(refreshState, 500);
})();
