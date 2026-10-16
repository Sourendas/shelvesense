async function health() {
  const el = document.getElementById("health");
  try {
    const r = await fetch("/api/health");
    const j = await r.json();
    el.textContent = `OK · ${j.products} SKUs · ${j.reviews} reviews · ${j.retriever} · LLM: ${j.amd && j.amd.configured ? 'AMD ' + j.amd.model : 'offline fallback'}`;
    el.classList.add("ok");
  } catch (e) {
    el.textContent = "server offline — run: python3 app/server.py";
  }
}

function pills(list, inferred) {
  if (!list || !list.length) return "<span class='meta'>—</span>";
  return list
    .map(
      (x) =>
        `<span class="tag-pill${inferred ? " inferred" : ""}">${escapeHtml(x)}</span>`
    )
    .join("");
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function loadCatalogue() {
  const r = await fetch("/api/catalogue");
  const j = await r.json();
  document.getElementById("cat-meta").textContent = `${j.count} products enriched`;
  const tbody = document.querySelector("#catalogue tbody");
  tbody.innerHTML = "";
  for (const p of j.products) {
    const src = (p.enriched && p.enriched.source) || {};
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><code>${escapeHtml(p.sku)}</code></td>
      <td>${escapeHtml(p.title)}<div class="meta">${escapeHtml(p.brand)} · $${p.price_usd}</div></td>
      <td>${pills(p.skin_type, src.skin_type === "inferred")}</td>
      <td>${pills(p.concerns, src.concerns === "inferred")}</td>
      <td>${pills((p.key_ingredients || []).slice(0, 4), false)}</td>
      <td>${p.enriched && p.enriched.avg_rating != null ? p.enriched.avg_rating : "—"}</td>
      <td class="meta">${escapeHtml(src.skin_type || "")}/${escapeHtml(src.concerns || "")}</td>
    `;
    tbody.appendChild(tr);
  }
}

async function askQuestion(q) {
  const answer = document.getElementById("answer");
  const recs = document.getElementById("recs");
  const cites = document.getElementById("cites");
  answer.classList.remove("empty");
  answer.textContent = "Thinking (local TF-IDF)…";
  recs.innerHTML = "";
  cites.innerHTML = "";
  const r = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: q, top_k: 5 }),
  });
  const j = await r.json();
  answer.innerHTML = escapeHtml(j.answer).replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  for (const rec of j.recommendations || []) {
    const div = document.createElement("div");
    div.className = "rec";
    div.innerHTML = `
      <h3>${escapeHtml(rec.sku)} — ${escapeHtml(rec.title)}</h3>
      <div class="meta">score ${rec.score} · ${escapeHtml(rec.brand || "")} · $${rec.price_usd}
        ${rec.avg_rating != null ? " · ★ " + rec.avg_rating : ""}</div>
      <p>${escapeHtml(rec.why || "")}</p>
      <div>${pills(rec.skin_type)}${pills(rec.concerns)}</div>
    `;
    recs.appendChild(div);
  }
  if (j.citations && j.citations.length) {
    const h = document.createElement("h3");
    h.textContent = "Citations";
    h.style.fontSize = "0.95rem";
    cites.appendChild(h);
  }
  for (const c of j.citations || []) {
    const div = document.createElement("div");
    div.className = "cite";
    div.innerHTML = `
      <h4>${escapeHtml(c.type)} · ${escapeHtml(c.sku)}
        ${c.review_id ? "(" + escapeHtml(c.review_id) + ")" : ""}
        · score ${c.score}</h4>
      <p>${escapeHtml(c.snippet || "")}</p>
    `;
    cites.appendChild(div);
  }
  const note = document.createElement("p");
  note.className = "meta";
  note.textContent = (j.llm && j.llm.used ? "[AMD " + j.llm.model + "] " : "") + (j.note || "");
  cites.appendChild(note);
}

document.getElementById("btn-load").addEventListener("click", () => loadCatalogue().catch(console.error));
document.getElementById("ask-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const q = document.getElementById("question").value.trim();
  if (q) askQuestion(q).catch(console.error);
});
document.querySelectorAll(".chip").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.getElementById("question").value = btn.dataset.q;
    askQuestion(btn.dataset.q).catch(console.error);
  });
});

health();
loadCatalogue().catch(console.error);
