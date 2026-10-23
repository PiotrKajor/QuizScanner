// Pilot w telefonie. Steruje tą samą sesją co panel nauczyciela; działa po
// sparowaniu kodem QR (ciasteczko z kluczem) albo na komputerze nauczyciela.
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

// Wibracja przy naciśnięciu: na telefonie od razu czuć, że przycisk zadziałał.
function buzz() { if (navigator.vibrate) navigator.vibrate(15); }

let phase = "idle";
let busy = false;

// Główny przycisk zmienia się z fazą: Start → Pokaż wynik → Następne.
const MAIN = {
  idle: { label: "t_start", action: "start", cls: "btn-ok" },
  question: { label: "t_reveal", action: "reveal", cls: "btn-primary" },
  reveal: { label: "t_next", action: "next", cls: "btn-ok" },
  podium: { label: "rm_restart", action: "reset", cls: "btn-ghost" },
};

$("mainBtn").onclick = async () => {
  if (busy) return;
  const m = MAIN[phase] || MAIN.idle;
  if (m.action === "reset" && !confirm(t("t_confirm_reset"))) return;
  busy = true; buzz();
  try { await ctl(m.action); } finally { busy = false; }
  refresh();
};
$("prevBtn").onclick = () => { buzz(); ctl("prev").then(refresh); };
$("nextBtn").onclick = () => { buzz(); ctl("next").then(refresh); };
$("resetBtn").onclick = () => {
  if (confirm(t("t_confirm_reset"))) ctl("reset").then(refresh);
};
$("drawBtn").onclick = async () => {
  buzz();
  const r = await ctl("draw");
  $("drawOut").innerHTML = r.ok
    ? `${esc(r.draw.name)}<small>${t("dr_left", { n: r.draw.left })}</small>`
    : `<small>${t("dr_empty")}</small>`;
};
$("loadBtn").onclick = async () => {
  const name = $("quizSel").value;
  if (name) await api("/api/load", { name });
  refresh();
};
$("classSel").onchange = async () => {
  const st = await api("/api/state?full=1");
  const reset = st.answered || (st.leaderboard || []).length;
  if (reset && !confirm(t("cl_confirm_switch"))) { loadLists(); return; }
  await api("/api/class/select", { id: $("classSel").value, reset: true });
  refresh();
};

async function loadLists() {
  const q = await api("/api/quizzes");
  $("quizSel").innerHTML = (q.quizzes || []).map(n =>
    `<option value="${esc(n)}" ${n === q.active ? "selected" : ""}>${esc(n)}</option>`).join("");
  const c = await api("/api/classes");
  $("classSel").innerHTML = (c.classes || []).map(k =>
    `<option value="${esc(k.id)}" ${k.id === c.active ? "selected" : ""}>${esc(k.name)} (${k.count})</option>`).join("");
}

function render(st) {
  phase = st.phase;
  const q = st.question;
  $("quizTitle").textContent = st.quiz_title || "QuizScanner";
  $("className").textContent = st.class_name || "";
  $("phase").textContent = t("ph_" + st.phase);
  $("phase").className = "phase " + st.phase;
  $("counter").textContent = st.total
    ? t("t_question_of", { n: st.index + 1, total: st.total }) : t("t_load_quiz_first");
  $("timeLeft").textContent = st.time_left != null ? Math.ceil(st.time_left) + " s" : "—";
  $("answered").textContent = st.class_size
    ? `${st.answered}/${st.class_size}` : st.answered;
  $("qtext").innerHTML = q ? tex(q.text) : "";
  $("opts").innerHTML = q ? [0, 1, 2, 3].filter(i => q.answers[i]).map(i => {
    const L = LETTERS[i];
    return `<div class="rm-opt opt-${L} ${q.correct === i ? "correct" : ""}">
      <span class="badge">${L}</span><span class="c">${tex(q.answers[i])}</span>
      <span class="num">${st.distribution[L] || 0}</span></div>`;
  }).join("") : "";

  const m = MAIN[st.phase] || MAIN.idle;
  const btn = $("mainBtn");
  btn.textContent = t(m.label);
  btn.className = m.cls + " rm-main-btn";
  ["mainBtn", "prevBtn", "nextBtn"].forEach(id => { $(id).disabled = !!st.auto_mode || !q; });
  if (st.phase === "podium") $("mainBtn").disabled = false;

  $("autoBar").classList.toggle("hidden", !st.auto_mode);
  if (st.auto_mode) $("autoBar").textContent = t("t_auto_running");

  const missing = st.missing || [];
  $("missingCard").classList.toggle("hidden", st.phase !== "question" || !missing.length);
  $("missingTitle").textContent = t("rm_missing", { n: missing.length });
  $("missing").innerHTML = missing.map(s => `<span>${esc(s.name)}</span>`).join("");

  const bar = $("restoreBar");
  bar.classList.toggle("hidden", !st.restored_at);
  if (st.restored_at && !bar.dataset.shown) {
    bar.dataset.shown = "1";
    bar.innerHTML = t("rs_restored", { time: new Date(st.restored_at * 1000).toLocaleTimeString().slice(0, 5) }) +
      ` <button class="btn-ghost" id="rsOk">${t("close")}</button>`;
    $("rsOk").onclick = () => ctl("dismiss_restore").then(refresh);
  }
}

async function refresh() {
  try {
    const r = await fetch("/api/state?full=1");
    if (r.status === 403) return showLocked();
    render(await r.json());
  } catch (e) { /* serwer chwilowo niedostępny */ }
}

let timer = null;
function showLocked() {
  $("lockedView").classList.remove("hidden");
  $("phase").classList.add("hidden");
  $("remoteView").classList.add("hidden");
  $("badKey").classList.toggle("hidden", !location.search.includes("bad=1"));
  if (timer) { clearInterval(timer); timer = null; }
}

(async function init() {
  await initLang();
  const who = await api("/api/whoami");
  if (!who.authorized) return showLocked();
  $("remoteView").classList.remove("hidden");
  loadLists();
  refresh();
  timer = setInterval(refresh, 600);
})();
