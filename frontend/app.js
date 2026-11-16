// app.js
// Plain JavaScript frontend for English TTS POC
// No frameworks, no build step. All logic lives here.

const API_BASE = "http://localhost:8000"; // backend base URL

// Elements
const fileInput = document.getElementById("file-input");
const uploadBtn = document.getElementById("upload-btn");
const uploadStatus = document.getElementById("upload-status");
const uploadSpinner = document.getElementById("upload-spinner");
const librarySection = document.getElementById("library");
const documentList = document.getElementById("document-list");
const chaptersSection = document.getElementById("chapters");
const chapterList = document.getElementById("chapter-list");
const transcriptPanel = document.getElementById("transcript-panel");
const transcriptDiv = document.getElementById("transcript");
const playerBar = document.getElementById("player-bar");
const audioPlayer = document.getElementById("audio-player");
const playPauseBtn = document.getElementById("play-pause");
const prevBtn = document.getElementById("prev-chapter");
const nextBtn = document.getElementById("next-chapter");
const playbackRateSelect = document.getElementById("playback-rate");
const currentTitle = document.getElementById("current-title");

let currentDocId = null;
let currentChapterId = null;
let chapterData = []; // {id, index, title, lang, statusObj, timing}
let pollControllers = {};

/** Utility helpers **/
function show(el) { el.classList.remove("hidden"); }
function hide(el) { el.classList.add("hidden"); }
function setStatus(msg, type = "") {
  uploadStatus.textContent = msg;
  uploadStatus.className = "status" + (type ? " " + type : "");
  show(uploadStatus);
}
function clearStatus() { hide(uploadStatus); }
function spinner(showIt) { if (showIt) show(uploadSpinner); else hide(uploadSpinner); }
function safeJSON(resp) { return resp.json().catch(() => ({})); }
function createBadge(text, cls) {
  const span = document.createElement("span");
  span.textContent = text;
  span.className = "badge " + cls;
  return span;
}
function confirmAction(message) {
  return Promise.resolve(window.confirm(message));
}
function safeLocalStorage(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* ignore */ }
}
function getLocalStorage(key, fallback) {
  try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; } catch (e) { return fallback; }
}

/** API wrappers **/
async function uploadDocument(file) {
  const form = new FormData();
  form.append("file", file);
  const resp = await fetch(`${API_BASE}/documents/`, {
    method: "POST",
    body: form,
  });
  if (!resp.ok) {
    const err = await safeJSON(resp);
    throw new Error(err.detail || "Upload failed");
  }
  return resp.json(); // returns document object with id
}

async function getDocument(id) {
  const resp = await fetch(`${API_BASE}/documents/${id}/`);
  if (!resp.ok) throw new Error("Unable to fetch document");
  return resp.json();
}

async function listDocuments() {
  const resp = await fetch(`${API_BASE}/documents/`);
  if (!resp.ok) throw new Error("Unable to list documents");
  return resp.json();
}

async function deleteDocument(id) {
  const resp = await fetch(`${API_BASE}/documents/${id}`, { method: "DELETE" });
  if (!resp.ok) throw new Error("Delete failed");
}

async function getChapters(docId) {
  const resp = await fetch(`${API_BASE}/documents/${docId}`);
  if (!resp.ok) throw new Error("Unable to get document details");
  // documented endpoint: GET /documents/{id}/chapters
  const chapResp = await fetch(`${API_BASE}/documents/${docId}/chapters`);
  if (!chapResp.ok) throw new Error("Unable to fetch chapters");
  return chapResp.json();
}

async function getAudioStatus(chapterId) {
  const resp = await fetch(`${API_BASE}/chapters/${chapterId}/audio/status?lang=en`);
  if (resp.status === 404) return { status: "not_requested" };
  if (!resp.ok) throw new Error("Audio status error");
  return resp.json();
}

async function postAudio(chapterId, force = false) {
  const url = `${API_BASE}/chapters/${chapterId}/audio?lang=en&force=${force}`;
  const resp = await fetch(url, { method: "POST" });
  if (!resp.ok) throw new Error("Audio request failed");
  return resp.json();
}

async function getAudio(chapterId) {
  return `${API_BASE}/chapters/${chapterId}/audio?lang=en`;
}

async function getTiming(chapterId) {
  const resp = await fetch(`${API_BASE}/chapters/${chapterId}/timing?lang=en`);
  if (!resp.ok) throw new Error("Timing fetch failed");
  return resp.json();
}

/** UI Rendering **/
function renderLibrary(docs) {
  documentList.innerHTML = "";
  docs.forEach(doc => {
    const li = document.createElement("li");
    const title = document.createElement("span");
    title.textContent = doc.title || doc.filename || "Untitled";
    title.tabIndex = 0;
    title.setAttribute("role", "button");
    title.addEventListener("click", () => loadDocument(doc.id));
    title.addEventListener("keypress", e => { if (e.key === "Enter") loadDocument(doc.id); });

    const badge = createBadge(doc.status, doc.status === "ready" ? "success" : "warning");
    const delBtn = document.createElement("button");
    delBtn.textContent = "Delete";
    delBtn.addEventListener("click", async () => {
      const ok = await confirmAction("Delete this document?");
      if (!ok) return;
      try {
        await deleteDocument(doc.id);
        loadLibrary();
      } catch (e) { alert(e.message); }
    });
    li.append(title, badge, delBtn);
    documentList.appendChild(li);
  });
  show(librarySection);
}

async function loadLibrary() {
  try {
    const docs = await listDocuments();
    renderLibrary(docs);
    // Restore last selected document if possible
    const lastDoc = getLocalStorage("lastDocId");
    if (lastDoc && docs.some(d => d.id === lastDoc)) {
      loadDocument(lastDoc);
    }
  } catch (e) {
    setStatus("Backend unreachable: " + e.message, "danger");
  }
}

async function loadDocument(id) {
  // cancel any ongoing polls
  cancelAllPolls();
  currentDocId = id;
  safeLocalStorage("lastDocId", id);
  try {
    const doc = await getDocument(id);
    // start polling for status if not ready
    if (doc.status === "uploaded" || doc.status === "extracting") {
      setStatus("Processing document, this can take a few minutes for scanned files...", "warning");
      spinner(true);
      const pollId = setInterval(async () => {
        try {
          const refreshed = await getDocument(id);
          if (refreshed.status === "ready") {
            clearInterval(pollId);
            spinner(false);
            clearStatus();
            loadChapters(id);
          } else if (refreshed.status === "failed") {
            clearInterval(pollId);
            spinner(false);
            setStatus("Document processing failed.", "danger");
          }
        } catch (e) { /* ignore transient */ }
      }, 3000);
      pollControllers.docPoll = pollId;
    } else if (doc.status === "ready") {
      loadChapters(id);
    } else {
      setStatus("Document status: " + doc.status, "danger");
    }
  } catch (e) {
    setStatus("Error loading document: " + e.message, "danger");
  }
}

async function loadChapters(docId) {
  try {
    const chapters = await getChapters(docId);
    chapterData = chapters.map(ch => ({ ...ch, statusObj: null, timing: null }));
    renderChapterList();
    // restore last chapter if saved
    const saved = getLocalStorage("lastChapter");
    if (saved && saved.docId === docId) {
      const chap = chapterData.find(c => c.id === saved.chapterId);
      if (chap) selectChapter(chap.id, saved.position);
    }
  } catch (e) {
    setStatus("Failed to load chapters: " + e.message, "danger");
  }
}

function renderChapterList() {
  chapterList.innerHTML = "";
  chapterData.forEach(ch => {
    const li = document.createElement("li");
    const title = document.createElement("span");
    title.textContent = `${ch.index + 1}. ${ch.title || "Untitled"}`;
    title.tabIndex = 0;
    title.setAttribute("role", "button");
    title.addEventListener("click", () => selectChapter(ch.id));
    title.addEventListener("keypress", e => { if (e.key === "Enter") selectChapter(ch.id); });

    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = "Loading...";
    // will be updated later via poll

    const playBtn = document.createElement("button");
    playBtn.textContent = "▶️";
    playBtn.addEventListener("click", () => handlePlay(ch.id));

    const regenBtn = document.createElement("button");
    regenBtn.textContent = "Regenerate";
    regenBtn.addEventListener("click", async () => {
      const ok = await confirmAction("Regenerate audio for this chapter?");
      if (!ok) return;
      await requestAudio(ch.id, true);
    });

    li.append(title, badge, playBtn, regenBtn);
    chapterList.appendChild(li);
    ch._badgeEl = badge; // store reference for later updates

    // start status poll for each chapter
    pollAudioStatus(ch);
  });
  show(chaptersSection);
}

function updateBadge(ch) {
  const badge = ch._badgeEl;
  if (!badge) return;
  const status = ch.statusObj?.status || "not_requested";
  badge.className = "badge";
  badge.textContent = "";
  if (status === "ready") {
    // duration provided in seconds
    const dur = ch.statusObj.duration_s || 0;
    const mins = Math.floor(dur / 60);
    const secs = Math.round(dur % 60).toString().padStart(2, "0");
    badge.textContent = `Ready (${mins}:${secs})`;
    badge.classList.add("success");
  } else if (status === "processing") {
    badge.textContent = "Generating...";
    badge.classList.add("warning");
  } else if (status === "failed") {
    badge.textContent = "Failed";
    badge.classList.add("danger");
  } else if (status === "not_requested") {
    badge.textContent = "No audio";
    badge.classList.add("warning");
  }
  if (ch.statusObj?.truncated) {
    const warn = document.createElement("span");
    warn.textContent = " Truncated";
    warn.className = "badge warning";
    badge.appendChild(warn);
  }
}

function pollAudioStatus(ch) {
  const poll = async () => {
    try {
      const status = await getAudioStatus(ch.id);
      ch.statusObj = status;
      updateBadge(ch);
      // if still processing, continue polling
      if (status.status === "processing") {
        // keep polling every 3s
        pollControllers[`chap-${ch.id}`] = setTimeout(poll, 3000);
      }
    } catch (e) { /* ignore */ }
  };
  poll();
}

function cancelAllPolls() {
  Object.values(pollControllers).forEach(id => clearInterval(id) || clearTimeout(id));
  pollControllers = {};
}

// /** Playback handling **/
// async function handlePlay(chapterId) {
//   // stop any existing playback and polling
//   if (currentChapterId && currentChapterId !== chapterId) {
//     stopCurrentPolling();
//   }
//   const ch = chapterData.find(c => c.id === chapterId);
//   if (!ch) return;
//   // ensure audio is ready (may need to request)
//   if (!ch.statusObj || ch.statusObj.status !== "ready") {
//     await requestAudio(chapterId, false);
//   }
//   // set source and play
//   const src = await getAudio(chapterId);
//   audioPlayer.src = src;
//   audioPlayer.play();
//   currentChapterId = chapterId;
//   safeLocalStorage("lastChapter", { docId: currentDocId, chapterId, position: 0 });
//   currentTitle.textContent = ch.title || `Chapter ${ch.index + 1}`;
//   show(playerBar);
//   // load transcript if not yet
//   if (!ch.timing) {
//     try {
//       const timing = await getTiming(chapterId);
//       ch.timing = timing;
//       renderTranscript(ch);
//     } catch (e) { console.warn("Timing fetch error", e); }
//   }
// }


async function handlePlay(chapterId) {
  if (currentChapterId && currentChapterId !== chapterId) {
    stopCurrentPolling();
  }
  const ch = chapterData.find(c => c.id === chapterId);
  if (!ch) return;

  currentChapterId = chapterId;
  safeLocalStorage("lastChapter", { docId: currentDocId, chapterId, position: 0 });
  currentTitle.textContent = ch.title || `Chapter ${ch.index + 1}`;
  show(playerBar);

  // Clear the old transcript immediately so it never shows another chapter
  transcriptDiv.textContent = "Loading transcript...";
  show(transcriptPanel);

  // Make sure audio exists; the status check comes from the server, not the cache
  const status = await getAudioStatus(chapterId);
  ch.statusObj = status;
  updateBadge(ch);
  if (status.status !== "ready") {
    await requestAudio(chapterId, false);
    transcriptDiv.textContent = "Generating audio... the transcript will appear when it is ready.";
    return; // requestAudio's poll starts playback when ready
  }

  audioPlayer.src = await getAudio(chapterId);
  audioPlayer.play();

  // Always redraw the transcript for THIS chapter (fetch only if not cached)
  if (!ch.timing) {
    try {
      ch.timing = await getTiming(chapterId);
    } catch (e) {
      transcriptDiv.textContent = "No transcript available.";
      return;
    }
  }
  if (currentChapterId === chapterId) renderTranscript(ch);
}

async function requestAudio(chapterId, force) {
  // POST request then poll until ready/failed
  try {
    await postAudio(chapterId, force);
    // start polling for status
    const poll = async () => {
      try {
        const status = await getAudioStatus(chapterId);
        const ch = chapterData.find(c => c.id === chapterId);
        if (ch) ch.statusObj = status;
        updateBadge(ch);
        if (status.status === "processing") {
          pollControllers[`poll-${chapterId}`] = setTimeout(poll, 3000);
        } else if (status.status === "ready") {
          // ready – if this chapter is the one we wanted to play, start playback
          if (currentChapterId === chapterId) {
            const src = await getAudio(chapterId);
            audioPlayer.src = src;
            audioPlayer.play();
            if (currentChapterId === chapterId) {
              const ch2 = chapterData.find(c => c.id === chapterId);
              if (ch2 && !ch2.timing) ch2.timing = await getTiming(chapterId);
              if (ch2) renderTranscript(ch2);
            }
          }
        } else if (status.status === "failed") {
          // show error badge already set
        }
      } catch (e) { console.error(e); }
    };
    poll();
  } catch (e) {
    alert("Audio request failed: " + e.message);
  }
}

function stopCurrentPolling() {
  // clear any chapter‑specific polling timeouts
  Object.keys(pollControllers).forEach(k => {
    if (k.startsWith("poll-")) {
      clearTimeout(pollControllers[k]);
      delete pollControllers[k];
    }
  });
}

/** Transcript rendering **/
function renderTranscript(ch) {
  transcriptDiv.innerHTML = "";
  if (!ch.timing) {
    transcriptDiv.textContent = "No transcript available.";
    return;
  }
  ch.timing.forEach(seg => {
    const span = document.createElement("span");
    span.textContent = seg.text + " ";
    span.dataset.start = seg.start_s;
    span.dataset.end = seg.end_s;
    span.addEventListener("click", () => {
      audioPlayer.currentTime = parseFloat(seg.start_s);
    });
    transcriptDiv.appendChild(span);
  });
  show(transcriptPanel);
}

function highlightCurrentSentence() {
  const time = audioPlayer.currentTime;
  const ch = chapterData.find(c => c.id === currentChapterId);
  if (!ch || !ch.timing) return;
  // binary search for index
  let lo = 0, hi = ch.timing.length - 1, idx = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    const seg = ch.timing[mid];
    if (time >= seg.start_s && time < seg.end_s) {
      idx = mid; break;
    } else if (time < seg.start_s) {
      hi = mid - 1;
    } else {
      lo = mid + 1;
    }
  }
  const spans = transcriptDiv.querySelectorAll("span");
  spans.forEach((s, i) => s.classList.toggle("active", i === idx));
  if (idx >= 0) {
    const active = spans[idx];
    active.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

/** Player controls **/
playPauseBtn.addEventListener("click", () => {
  if (audioPlayer.paused) audioPlayer.play(); else audioPlayer.pause();
});
prevBtn.addEventListener("click", () => {
  if (!currentChapterId) return;
  const curIdx = chapterData.findIndex(c => c.id === currentChapterId);
  if (curIdx > 0) handlePlay(chapterData[curIdx - 1].id);
});
nextBtn.addEventListener("click", () => {
  if (!currentChapterId) return;
  const curIdx = chapterData.findIndex(c => c.id === currentChapterId);
  if (curIdx < chapterData.length - 1) handlePlay(chapterData[curIdx + 1].id);
});
playbackRateSelect.addEventListener("change", () => {
  audioPlayer.playbackRate = parseFloat(playbackRateSelect.value);
});

audioPlayer.addEventListener("timeupdate", highlightCurrentSentence);

audioPlayer.addEventListener("ended", () => {
  // offer next chapter play – just enable next button UI (already enabled)
});

/** Upload flow **/
uploadBtn.addEventListener("click", async () => {
  const file = fileInput.files[0];
  if (!file) { alert("Select a file first"); return; }
  clearStatus();
  spinner(true);
  try {
    const doc = await uploadDocument(file);
    spinner(false);
    setStatus("Upload successful. Document ID: " + doc.id, "success");
    // reload library to show new doc
    loadLibrary();
  } catch (e) {
    spinner(false);
    setStatus("Upload error: " + e.message, "danger");
  }
});

/** Init **/
window.addEventListener("load", () => {
  loadLibrary();
});

// Clean up when leaving page
window.addEventListener("beforeunload", () => {
  cancelAllPolls();
});
