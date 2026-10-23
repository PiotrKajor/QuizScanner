// Edytor quizów, ustawień i listy uczniów.
const LETTERS = ["A", "B", "C", "D"];
const $ = id => document.getElementById(id);
const MEDIA_MAX_MB = 40;

const DEFAULT_SETTINGS = {
  default_time: 20, default_points: 1000,
  shuffle_questions: false, shuffle_answers: false,
  show_distribution: true, auto_reveal_s: 6, auto_gap_s: 3,
};

let quiz = { title: "", settings: Object.assign({}, DEFAULT_SETTINGS), questions: [] };
let currentName = null;
let mediaTargetIndex = null;   // do którego pytania wgrywamy plik

function esc(s) {
  return (s || "").replace(/[&<>"]/g, c => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
function toast(msg) {
  const el = $("toast"); el.textContent = msg; el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 1800);
}
async function api(path, body) {
  const opt = body ? { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body) } : {};
  return (await fetch(path, opt)).json();
}

// ---------- normalizacja ----------
function normalize(q) {
  q = q || {};
  return {
    title: q.title || "",
    settings: Object.assign({}, DEFAULT_SETTINGS, q.settings || {}),
    questions: (q.questions || []).map(x => ({
      text: x.text || "",
      answers: [0, 1, 2, 3].map(i => (x.answers && x.answers[i]) || ""),
      correct: (typeof x.correct === "number") ? x.correct : 0,
      time: x.time || 20,
      points: x.points || 1000,
      media: (x.media && x.media.file) ? { file: x.media.file, type: x.media.type || "image" } : null,
    })),
  };
}

// ---------- lista quizów ----------
async function loadQuizList() {
  const r = await api("/api/quizzes");
  const ul = $("quizList"); ul.innerHTML = "";
  (r.quizzes || []).forEach(name => {
    const li = document.createElement("li");
    li.textContent = name;
    if (name === currentName) li.classList.add("active");
    li.onclick = () => selectQuiz(name);
    ul.appendChild(li);
  });
  if (!r.quizzes || !r.quizzes.length)
    ul.innerHTML = `<li class="muted">${t("e_no_quizzes")}</li>`;
}

async function selectQuiz(name) {
  quiz = normalize(await api("/api/quiz?name=" + encodeURIComponent(name)));
  currentName = name;
  showWarnings("importWarn", null);
  renderAll();
}

// Plik z dysku jako data:URL (tak serwer przyjmuje przesyłane pliki).
function readAsDataUrl(f) {
  return new Promise(res => {
    const fr = new FileReader(); fr.onload = () => res(fr.result); fr.readAsDataURL(f);
  });
}

// Panel z podsumowaniem importu i ostrzeżeniami do poprawienia.
function showWarnings(id, head, list) {
  const el = $(id);
  if (!head) { el.classList.add("hidden"); return; }
  el.innerHTML = `<b>${esc(head)}</b>` + ((list && list.length)
    ? `<ul>${list.map(w => `<li>${esc(w)}</li>`).join("")}</ul>` : "");
  el.classList.remove("hidden");
}

// ---------- render ----------
function renderAll() {
  $("quizTitle").value = quiz.title;
  $("editingName").textContent = currentName
    ? t("e_editing_file") + " " + currentName : t("e_unsaved");
  renderSettings();
  renderQuestions();
  loadQuizList();
}

function renderSettings() {
  const s = quiz.settings;
  $("setTime").value = s.default_time;
  $("setPoints").value = s.default_points;
  $("setReveal").value = s.auto_reveal_s;
  $("setGap").value = s.auto_gap_s;
  $("setShuffleQ").checked = !!s.shuffle_questions;
  $("setShuffleA").checked = !!s.shuffle_answers;
  $("setShowDist").checked = !!s.show_distribution;
}

function mediaRow(q, qi) {
  if (q.media && q.media.file) {
    const src = "/media/" + encodeURIComponent(q.media.file);
    const prev = q.media.type === "video"
      ? `<video src="${src}" class="mprev" muted></video>`
      : `<img src="${src}" class="mprev" alt="">`;
    return `<div class="media-row">${prev}
      <button class="btn-danger" data-act="media-del" data-qi="${qi}">${t("e_media_remove")}</button></div>`;
  }
  return `<div class="media-row">
    <button class="btn-ghost" data-act="media-add" data-qi="${qi}">${t("e_media_add")}</button>
    <span class="muted">${t("e_media_hint")}</span></div>`;
}

function renderQuestions() {
  const box = $("questions"); box.innerHTML = "";
  quiz.questions.forEach((q, qi) => {
    const card = document.createElement("div");
    card.className = "qcard";
    card.innerHTML = `
      <div class="qrow">
        <span class="qnum">${t("e_question_n", { n: qi + 1 })}</span>
        <div class="qtools">
          <button class="btn-ghost" data-act="up" data-qi="${qi}">▲</button>
          <button class="btn-ghost" data-act="down" data-qi="${qi}">▼</button>
          <button class="btn-danger" data-act="del" data-qi="${qi}">🗑</button>
        </div>
      </div>
      <textarea class="text q-text" data-qi="${qi}" placeholder="${t("e_question_ph")}">${esc(q.text)}</textarea>
      <label class="field mt" >${t("e_media")}</label>
      ${mediaRow(q, qi)}
      <div class="opts-ed">
        ${[0, 1, 2, 3].map(ai => `
          <div class="opt-ed opt-${LETTERS[ai]}">
            <span class="badge">${LETTERS[ai]}</span>
            <input class="text q-ans" data-qi="${qi}" data-ai="${ai}"
                   placeholder="${t("e_answer_ph", { letter: LETTERS[ai] })}" value="${esc(q.answers[ai])}">
            <label class="pick"><input type="radio" name="correct-${qi}" value="${ai}"
                   ${q.correct === ai ? "checked" : ""}> ${t("e_correct")}</label>
          </div>`).join("")}
      </div>
      <div class="meta-row">
        <div class="m"><label class="field">${t("e_time_s")}</label>
          <input class="text q-time" type="number" min="0" data-qi="${qi}" value="${q.time}"></div>
        <div class="m"><label class="field">${t("e_points")}</label>
          <input class="text q-points" type="number" min="0" step="100" data-qi="${qi}" value="${q.points}"></div>
      </div>`;
    box.appendChild(card);
  });

  box.querySelectorAll("button[data-act]").forEach(b => {
    b.onclick = () => {
      syncFromDom();
      const qi = +b.dataset.qi, act = b.dataset.act;
      if (act === "del") quiz.questions.splice(qi, 1);
      else if (act === "up" && qi > 0)
        [quiz.questions[qi - 1], quiz.questions[qi]] = [quiz.questions[qi], quiz.questions[qi - 1]];
      else if (act === "down" && qi < quiz.questions.length - 1)
        [quiz.questions[qi + 1], quiz.questions[qi]] = [quiz.questions[qi], quiz.questions[qi + 1]];
      else if (act === "media-add") { mediaTargetIndex = qi; $("mediaFile").click(); return; }
      else if (act === "media-del") quiz.questions[qi].media = null;
      renderQuestions();
    };
  });
}

function syncFromDom() {
  quiz.title = $("quizTitle").value;
  document.querySelectorAll(".q-text").forEach(el => quiz.questions[+el.dataset.qi].text = el.value);
  document.querySelectorAll(".q-ans").forEach(el => quiz.questions[+el.dataset.qi].answers[+el.dataset.ai] = el.value);
  document.querySelectorAll(".q-time").forEach(el => quiz.questions[+el.dataset.qi].time = +el.value || 0);
  document.querySelectorAll(".q-points").forEach(el => quiz.questions[+el.dataset.qi].points = +el.value || 0);
  document.querySelectorAll('input[type=radio]:checked').forEach(el => {
    const qi = +el.name.split("-")[1]; quiz.questions[qi].correct = +el.value;
  });
  quiz.settings = {
    default_time: +$("setTime").value || 0,
    default_points: +$("setPoints").value || 0,
    auto_reveal_s: +$("setReveal").value || 0,
    auto_gap_s: +$("setGap").value || 0,
    shuffle_questions: $("setShuffleQ").checked,
    shuffle_answers: $("setShuffleA").checked,
    show_distribution: $("setShowDist").checked,
  };
}

// ---------- media ----------
$("mediaFile").onchange = async () => {
  const f = $("mediaFile").files[0];
  $("mediaFile").value = "";
  if (!f || mediaTargetIndex == null) return;
  if (f.size > MEDIA_MAX_MB * 1024 * 1024) { toast(t("e_media_too_big", { mb: MEDIA_MAX_MB })); return; }
  const dataUrl = await new Promise(res => {
    const fr = new FileReader(); fr.onload = () => res(fr.result); fr.readAsDataURL(f);
  });
  const r = await api("/api/media", { data: dataUrl, name: f.name });
  if (!r.ok) { toast(t("e_media_bad_type")); return; }
  syncFromDom();
  quiz.questions[mediaTargetIndex].media = { file: r.file, type: r.type };
  mediaTargetIndex = null;
  renderQuestions();
};

// ---------- akcje quizu ----------
$("addQ").onclick = () => {
  syncFromDom();
  const s = quiz.settings;
  quiz.questions.push({
    text: "", answers: ["", "", "", ""], correct: 0,
    time: s.default_time, points: s.default_points, media: null,
  });
  renderQuestions();
};
$("applyAll").onclick = () => {
  syncFromDom();
  quiz.questions.forEach(q => {
    q.time = quiz.settings.default_time;
    q.points = quiz.settings.default_points;
  });
  renderQuestions(); toast(t("s_applied"));
};
$("newQuiz").onclick = () => {
  quiz = { title: "", settings: Object.assign({}, DEFAULT_SETTINGS), questions: [] };
  currentName = null; showWarnings("importWarn", null); renderAll();
};

// Import z Worda (.docx) lub pliku tekstowego: wynik trafia do edytora jako
// nowy, niezapisany quiz — nauczyciel go przegląda i dopiero wtedy zapisuje.
$("wordBtn").onclick = () => $("wordFile").click();
$("wordFile").onchange = async () => {
  const f = $("wordFile").files[0];
  $("wordFile").value = "";
  if (!f) return;
  const r = await api("/api/quiz/parse", { name: f.name, data: await readAsDataUrl(f) });
  if (!r.ok) { toast(t("wi_failed") + " " + (r.error || "")); return; }
  quiz = normalize(r.quiz);
  currentName = null;
  renderAll();
  showWarnings("importWarn", t("wi_done", { n: quiz.questions.length }), r.warnings);
};
$("saveQuiz").onclick = async () => {
  syncFromDom();
  const r = await api("/api/quiz", { name: currentName || (quiz.title || "quiz"), quiz });
  currentName = r.name; renderAll(); toast(t("e_saved") + " " + r.name);
};
$("dupQuiz").onclick = async () => {
  syncFromDom();
  const r = await api("/api/quiz", { name: (quiz.title || "quiz") + " kopia", quiz });
  currentName = r.name; renderAll(); toast(t("e_copy_made") + " " + r.name);
};
$("delQuiz").onclick = async () => {
  if (!currentName) { $("newQuiz").onclick(); return; }
  if (!confirm(t("e_confirm_delete", { name: currentName }))) return;
  await api("/api/quiz/delete", { name: currentName });
  currentName = null; $("newQuiz").onclick(); toast(t("e_deleted"));
};

// zapis do pliku / wczytanie z pliku (dzielenie się quizem)
$("exportQuiz").onclick = async () => {
  syncFromDom();
  const name = currentName || (quiz.title || "quiz");
  await api("/api/quiz", { name, quiz });     // najpierw zapisz bieżący stan
  currentName = name; renderAll();
  window.open("/api/quiz/export?name=" + encodeURIComponent(name), "_blank");
};
$("importBtn").onclick = () => $("importFile").click();
$("importFile").onchange = async () => {
  const f = $("importFile").files[0];
  $("importFile").value = "";
  if (!f) return;
  try {
    const bundle = JSON.parse(await f.text());
    if (!bundle || !Array.isArray(bundle.questions)) throw new Error("bad");
    const base = (f.name || "quiz").replace(/\.(quiz|json)$/i, "");
    const r = await api("/api/quiz/import", { name: bundle.title || base, quiz: bundle });
    if (!r.ok) throw new Error("bad");
    await selectQuiz(r.name);
    toast(t("e_imported"));
  } catch (e) { toast(t("e_import_failed")); }
};

$("toTeacher").onclick = () => location.href = "/teacher";

// ---------- zakładki ----------
$("tabQuiz").onclick = () => switchTab("quiz");
$("tabRoster").onclick = () => switchTab("roster");
function switchTab(tab) {
  $("tabQuiz").classList.toggle("active", tab === "quiz");
  $("tabRoster").classList.toggle("active", tab === "roster");
  $("quizView").classList.toggle("hidden", tab !== "quiz");
  $("rosterView").classList.toggle("hidden", tab !== "roster");
  if (tab === "roster") loadRoster();
}

// ---------- klasy i uczniowie ----------
let roster = {};
let currentClass = null;      // id edytowanej klasy (null = nowa, niezapisana)
let activeClass = null;       // klasa, z którą toczy się gra

async function loadRoster(id) {
  const r = await api("/api/classes");
  activeClass = r.active;
  if (id === undefined) id = currentClass || r.active;
  const ul = $("classList"); ul.innerHTML = "";
  (r.classes || []).forEach(c => {
    const li = document.createElement("li");
    li.innerHTML = `<span>${c.id === r.active ? "● " : ""}${esc(c.name)}</span><span class="cnt">${c.count}</span>`;
    if (c.id === id) li.classList.add("active");
    li.title = c.id === r.active ? t("cl_active") : "";
    li.onclick = () => loadRoster(c.id);
    ul.appendChild(li);
  });
  if (id) {
    const c = await api("/api/class?id=" + encodeURIComponent(id));
    currentClass = c.id; roster = c.students; $("className").value = c.name;
  }
  showWarnings("rosterWarn", null);
  renderRoster();
}
function renderRoster() {
  const body = $("rosterBody"); body.innerHTML = "";
  Object.keys(roster).map(Number).sort((a, b) => a - b).forEach(id => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><input class="text r-id" type="number" value="${id}" style="width:70px"></td>
      <td><input class="text r-name" value="${esc(roster[id])}"></td>
      <td><button class="btn-danger r-del">✕</button></td>`;
    tr.querySelector(".r-del").onclick = () => { syncRoster(); delete roster[id]; renderRoster(); };
    body.appendChild(tr);
  });
}
function syncRoster() {
  const next = {};
  document.querySelectorAll("#rosterBody tr").forEach(tr => {
    const id = tr.querySelector(".r-id").value;
    if (id !== "") next[+id] = tr.querySelector(".r-name").value;
  });
  roster = next;
}
$("addStudent").onclick = () => {
  syncRoster();
  const next = Object.keys(roster).length ? Math.max(...Object.keys(roster).map(Number)) + 1 : 0;
  roster[next] = ""; renderRoster();
};
async function saveClass() {
  syncRoster();
  const name = $("className").value.trim();
  if (!name) { toast(t("cl_name_needed")); $("className").focus(); return null; }
  const r = await api("/api/class/save", { id: currentClass, name, students: roster });
  if (!r.ok) { toast(r.error === "exists" ? t("cl_exists") : t("cl_name_needed")); return null; }
  currentClass = r.id;
  await loadRoster(r.id);
  return r.id;
}
$("saveRoster").onclick = async () => {
  if (await saveClass()) toast(t("e_roster_saved"));
};
$("newClass").onclick = () => {
  currentClass = null; roster = {};
  $("className").value = "";
  document.querySelectorAll("#classList li").forEach(li => li.classList.remove("active"));
  renderRoster();
  $("className").focus();
};
$("delClass").onclick = async () => {
  if (!currentClass) { loadRoster(activeClass); return; }
  if (!confirm(t("cl_confirm_delete", { name: $("className").value }))) return;
  const r = await api("/api/class/delete", { id: currentClass });
  if (!r.ok) { toast(t("cl_last")); return; }
  currentClass = null; loadRoster(); toast(t("e_deleted"));
};
$("rosterImportBtn").onclick = () => $("rosterFile").click();
$("rosterFile").onchange = async () => {
  const f = $("rosterFile").files[0];
  $("rosterFile").value = "";
  if (!f) return;
  const r = await api("/api/roster/import", { name: f.name, data: await readAsDataUrl(f) });
  if (!r.ok) { toast(t("ri_failed") + " " + (r.error || "")); return; }
  roster = r.students;
  if (!$("className").value.trim()) $("className").value = f.name.replace(/\.[^.]+$/, "");
  renderRoster();
  showWarnings("rosterWarn", t("ri_done", { n: Object.keys(roster).length }), r.warnings);
};
$("rosterExport").onclick = () => {
  if (!currentClass) { toast(t("cl_save_first")); return; }
  window.open("/api/roster.csv?id=" + encodeURIComponent(currentClass), "_blank");
};
$("cardsBtn").onclick = async () => {
  syncRoster();
  if (!Object.keys(roster).length) { toast(t("e_add_students_first")); return; }
  const id = await saveClass();
  if (!id) return;
  toast(t("e_generating_pdf"));
  window.open("/api/cards.pdf?class=" + encodeURIComponent(id), "_blank");
};

// ---------- język i motyw ----------
$("langSel").onchange = async () => {
  await api("/api/settings", { lang: $("langSel").value });
  setLang($("langSel").value);
};
$("themeSel").onchange = async () => {
  setTheme($("themeSel").value);
  await api("/api/settings", { theme: $("themeSel").value });
};
document.addEventListener("i18n:changed", () => {
  fillThemeSelect($("themeSel"));
  if (quiz) renderAll();
});

// ---------- przybornik matematyczny ----------
$("mathToggle").onclick = () => {
  const on = $("mathPanel").classList.toggle("collapsed");
  $("mathToggle").textContent = t(on ? "mb_show" : "mb_hide");
};

// ---------- start ----------
(async function init() {
  await initLang();
  fillThemeSelect($("themeSel"));
  $("themeSel").value = document.documentElement.dataset.theme || "dark";
  MathBar.mount($("mathBox"));
  $("langSel").value = document.documentElement.lang;
  const r = await api("/api/quizzes");
  if (r.quizzes && r.quizzes.length) await selectQuiz(r.active || r.quizzes[0]);
  else { quiz = normalize({ title: "" }); renderAll(); }
})();
