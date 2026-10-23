// Widok tablicy (rzutnik). Odpytuje /api/state i renderuje fazę.
const LETTERS = ["A", "B", "C", "D"];
const root = document.getElementById("root");
let last = "";

function esc(s) {
  return (s || "").replace(/[&<>"]/g, c => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function pips(total, index) {
  let out = "";
  for (let i = 0; i < total; i++) {
    const cls = i < index ? "done" : (i === index ? "cur" : "");
    out += `<span class="pip ${cls}"></span>`;
  }
  return `<div class="pips">${out}</div>`;
}

// Zdjęcie lub film dołączony do pytania.
function mediaBlock(q) {
  const m = q.media;
  if (!m || !m.file) return "";
  const src = "/media/" + encodeURIComponent(m.file);
  if (m.type === "video") {
    return `<div class="qmedia"><video src="${src}" autoplay muted loop playsinline></video></div>`;
  }
  return `<div class="qmedia"><img src="${src}" alt=""></div>`;
}

function optionTile(i, text, st) {
  const q = st.question;
  const reveal = st.phase === "reveal";
  const isCorrect = reveal && q.correct === i;
  const dim = reveal && q.correct != null && q.correct !== i;
  const showDist = reveal && st.show_distribution !== false;
  const count = st.distribution[LETTERS[i]] || 0;
  const maxCount = Math.max(1, ...Object.values(st.distribution));
  const barW = showDist ? Math.round(100 * count / maxCount) : 0;
  return `<div class="opt opt-${LETTERS[i]} ${isCorrect ? "correct" : ""} ${dim ? "dim" : ""}">
    <span class="badge">${LETTERS[i]}</span>
    <span class="txt">${tex(text)}</span>
    <span class="check">✓</span>
    ${showDist ? `<span class="count">${count}</span><span class="dist" style="width:${barW}%"></span>` : ""}
  </div>`;
}

function renderQuestion(st) {
  const q = st.question;
  const low = st.time_left != null && st.time_left <= 5;
  const barW = (st.time_left != null && q.time) ? Math.max(0, 100 * st.time_left / q.time) : 100;
  const tiles = [0, 1, 2, 3].map(i => optionTile(i, q.answers[i] || "", st)).join("");
  const hasMedia = q.media && q.media.file;
  return `<div class="board-wrap">
    <div class="board-top">
      <div class="board-title">${esc(st.quiz_title)}</div>
      ${pips(st.total, st.index)}
      <div class="time-chip ${low ? "low" : ""}">${st.time_left != null ? Math.ceil(st.time_left) + "s" : "—"}</div>
    </div>
    <div class="time-bar"><i style="width:${barW}%"></i></div>
    <div class="kicker">${t("b_question_of", { n: st.index + 1, total: st.total })}</div>
    <div class="qtext ${hasMedia ? "with-media" : ""}">${tex(q.text)}</div>
    ${mediaBlock(q)}
    <div class="answers ${hasMedia ? "compact" : ""}">${tiles}</div>
    <div class="board-foot">
      <span class="chip">◎ ${t("b_scanned")} <b>${st.answered}</b></span>
      ${st.phase === "reveal" && q.correct != null
        ? `<span class="chip">${t("b_correct")} <span class="badge badge-${LETTERS[q.correct]}">${LETTERS[q.correct]}</span> ${tex(q.answers[q.correct])}</span>` : ""}
    </div>
  </div>`;
}

function renderIdle(st) {
  if (!st.question) {
    return `<div class="center-screen">
      <img class="idle-logo" src="/static/logo.svg" alt="">
      <div class="kicker">QuizScanner</div>
      <h1>${esc(st.quiz_title || t("b_ready"))}</h1>
      <p>${t("b_load_hint")}</p>
      <div class="scanline"></div>
    </div>`;
  }
  return `<div class="center-screen">
    <div class="kicker">${t("b_question_of", { n: st.index + 1, total: st.total })}</div>
    <h1>${tex(st.question.text)}</h1>
    <div class="scanline"></div>
    <p>${t("b_prepare")}</p>
  </div>`;
}

function renderPodium(st) {
  const rows = st.leaderboard.map((r, i) => `
    <div class="rank-row ${i < 3 ? "top" + (i + 1) : ""}">
      <span class="pos">${i + 1}</span>
      <span class="who">${esc(r.name)}</span>
      <span class="pts">${r.score} pkt</span>
    </div>`).join("");
  return `<div class="center-screen">
    <div class="kicker">${t("b_end_kicker")}</div>
    <h1>${t("b_standings")}</h1>
    <div class="podium">${rows || `<div class="rank-row"><span class="who">${t("b_no_results")}</span></div>`}</div>
  </div>`;
}

function render(st) {
  if (st.phase === "podium") return renderPodium(st);
  if (st.phase === "question" || st.phase === "reveal") return renderQuestion(st);
  return renderIdle(st);
}

// ---- dźwięki ----
// Tablica reaguje na zmiany stanu, a nie na kliknięcia, więc sygnały
// wyzwalamy porównując kolejne odpowiedzi serwera.
let prev = { phase: null, index: null, sec: null };

function cues(st) {
  if (!Sound.enabled) return;
  const sec = st.time_left != null ? Math.ceil(st.time_left) : null;

  if (st.phase !== prev.phase || st.index !== prev.index) {
    if (st.phase === "question") Sound.play("start");
    else if (st.phase === "reveal") Sound.play("reveal");
    else if (st.phase === "podium") Sound.play("podium");
    else if (prev.phase === "reveal") Sound.play("next");
  } else if (st.phase === "question" && sec != null && sec !== prev.sec) {
    // Odliczanie: ostatnie pięć sekund, ostatnia wyraźnie wyżej.
    if (sec === 0) Sound.play("timeup");
    else if (sec <= 5) Sound.play(sec === 1 ? "tickLast" : "tick");
  }
  prev = { phase: st.phase, index: st.index, sec };
}

// Przeglądarka nie zagra nic, dopóki ktoś nie kliknie w stronę.
function soundGate() {
  const el = document.getElementById("soundGate");
  if (!el) return;
  el.classList.toggle("hidden", !Sound.blocked);
  el.textContent = t("b_sound_locked");
}
document.addEventListener("pointerdown", () => { Sound.unlock(); soundGate(); });
document.addEventListener("keydown", () => { Sound.unlock(); soundGate(); });

// ---- losowanie ucznia ----
// Serwer zwraca wylosowanego ucznia przez kilka sekund; tablica pokazuje
// krótką animację przewijania imion i (opcjonalnie) czyta wynik na głos.
let drawSeq;               // undefined = pierwszy odczyt (bez animacji po odświeżeniu)
let drawHide = null;
let serverSettings = {};

function speak(name) {
  if (!serverSettings.speak_draw || !window.speechSynthesis) return;
  const lang = document.documentElement.lang;
  // Tylko głosy zainstalowane w systemie (localService) — aplikacja działa
  // offline i nie wysyła imion uczniów do żadnej usługi w sieci.
  const voice = speechSynthesis.getVoices().find(v => v.localService && v.lang.startsWith(lang));
  if (!voice) return;
  const u = new SpeechSynthesisUtterance(name);
  u.voice = voice; u.lang = voice.lang; u.rate = .95;
  speechSynthesis.cancel();
  speechSynthesis.speak(u);
}

function showDraw(d, animate) {
  const box = document.getElementById("drawOverlay");
  const el = document.getElementById("drawName");
  clearTimeout(drawHide);
  box.classList.remove("hidden");
  el.classList.remove("final");
  const finish = () => {
    el.textContent = d.name;
    void el.offsetWidth;            // restart animacji „pop"
    el.classList.add("final");
    if (Sound.enabled) Sound.play("drawn");
    speak(d.name);
    drawHide = setTimeout(() => box.classList.add("hidden"), 8000);
  };
  const pool = (d.pool || []).filter(n => n !== d.name);
  if (!animate || pool.length < 2) return finish();
  // Coraz wolniejsze przewijanie imion, jak koło losujące.
  let delay = 50, spent = 0;
  const step = () => {
    el.textContent = pool[Math.floor(Math.random() * pool.length)];
    if (Sound.enabled) Sound.play("roll");
    spent += delay;
    delay *= 1.12;
    if (spent < 2200) setTimeout(step, delay); else finish();
  };
  step();
}
document.getElementById("drawOverlay").onclick = () => {
  clearTimeout(drawHide);
  document.getElementById("drawOverlay").classList.add("hidden");
};

function checkDraw(st) {
  const d = st.draw;
  if (d && d.seq !== drawSeq && drawSeq !== undefined) showDraw(d, true);
  drawSeq = d ? d.seq : (drawSeq === undefined ? null : drawSeq);
}

// ---- pasek tablicy ----
const ZOOM_MIN = 0.8, ZOOM_MAX = 1.75, ZOOM_STEP = 0.15;
let zoom = 1;
try { zoom = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, +localStorage.getItem("qs_zoom") || 1)); } catch (e) { }

function applyZoom() {
  document.documentElement.style.setProperty("--zoom", zoom);
  document.getElementById("zVal").textContent = Math.round(zoom * 100) + "%";
  try { localStorage.setItem("qs_zoom", zoom); } catch (e) { }
}
function changeZoom(dir) {
  zoom = Math.round(Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, zoom + dir * ZOOM_STEP)) * 100) / 100;
  applyZoom();
}
const bctl = document.getElementById("bctl");
let bctlHide = null;
function showBar() {
  bctl.classList.add("show");
  clearTimeout(bctlHide);
  bctlHide = setTimeout(() => { if (!bctl.matches(":hover")) bctl.classList.remove("show"); }, 3000);
}
document.addEventListener("pointermove", showBar);
document.addEventListener("pointerdown", showBar);
bctl.addEventListener("mouseleave", showBar);
document.getElementById("zIn").onclick = () => changeZoom(1);
document.getElementById("zOut").onclick = () => changeZoom(-1);
document.getElementById("bFull").onclick = () => {
  if (document.fullscreenElement) document.exitFullscreen();
  else document.documentElement.requestFullscreen().catch(() => { });
};
document.addEventListener("keydown", e => {
  if (e.target.tagName === "SELECT") return;
  if (e.key === "+" || e.key === "=") changeZoom(1);
  else if (e.key === "-") changeZoom(-1);
  else if (e.key === "f" || e.key === "F") document.getElementById("bFull").onclick();
});

// Sterowanie z tablicy: tylko komputer nauczyciela i sparowane urządzenia.
let canControl = false;
let boardPhase = "idle";
const ctl = (action, extra) => fetch("/api/control", {
  method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify(Object.assign({ action }, extra || {})),
}).then(tick);
const MAIN_ACTION = { idle: ["start", "t_start"], question: ["reveal", "t_reveal"],
  reveal: ["next", "t_next"], podium: ["reset", "t_reset"] };
document.getElementById("bPrev").onclick = () => ctl("prev");
document.getElementById("bNext").onclick = () => ctl("next");
document.getElementById("bDraw").onclick = () => ctl("draw");
document.getElementById("bMain").onclick = () => {
  const [action] = MAIN_ACTION[boardPhase] || MAIN_ACTION.idle;
  if (action === "reset" && !confirm(t("t_confirm_reset"))) return;
  ctl(action);
};
document.getElementById("bGoto").onchange = e => ctl("goto", { index: +e.target.value });

let outlineKey = "";
async function refreshControls(st) {
  if (!canControl) return;
  boardPhase = st.phase;
  const [, label] = MAIN_ACTION[st.phase] || MAIN_ACTION.idle;
  document.getElementById("bMain").textContent = t(label);
  const sel = document.getElementById("bGoto");
  const key = st.quiz_title + st.total + document.documentElement.lang;
  if (key !== outlineKey) {
    outlineKey = key;
    try {
      const full = await (await fetch("/api/state?full=1")).json();
      sel.innerHTML = (full.outline || []).map((txt, i) =>
        `<option value="${i}">${i + 1}. ${esc(txt.replace(/\$/g, ""))}</option>`).join("");
    } catch (e) { }
  }
  if (document.activeElement !== sel) sel.value = st.index;
}

async function tick() {
  try {
    const st = await (await fetch("/api/state")).json();
    cues(st);
    checkDraw(st);
    refreshControls(st);
    const key = document.documentElement.lang + st.phase + st.index + st.answered
      + JSON.stringify(st.distribution)
      + (st.phase === "podium" ? JSON.stringify(st.leaderboard) : "");
    if (key !== last) { root.innerHTML = render(st); last = key; }
    else {
      // płynna aktualizacja samego timera bez przerysowania (nie przerywa filmu)
      const chip = root.querySelector(".time-chip");
      const bar = root.querySelector(".time-bar > i");
      if (chip && st.time_left != null && st.question) {
        chip.textContent = Math.ceil(st.time_left) + "s";
        chip.classList.toggle("low", st.time_left <= 5);
        if (bar) bar.style.width = Math.max(0, 100 * st.time_left / st.question.time) + "%";
      }
    }
  } catch (e) { /* serwer chwilowo niedostępny */ }
}

// Język, motyw i dźwięk zmienia się w panelu nauczyciela — tablica dopytuje,
// żeby ustawienia działały też na drugim komputerze przy rzutniku.
async function pollSettings() {
  try {
    serverSettings = applyServerSettings(await (await fetch("/api/settings")).json());
    soundGate();
  } catch (e) { }
}

(async function init() {
  serverSettings = await initLang();
  applyZoom();
  try {
    canControl = (await (await fetch("/api/whoami")).json()).authorized;
  } catch (e) { }
  bctl.classList.toggle("ctl", canControl);
  showBar();
  soundGate();
  tick();
  setInterval(tick, 350);
  setInterval(pollSettings, 2000);
})();
