(() => {
  const source = document.getElementById("source");
  const form = document.getElementById("composeForm");
  const output = document.getElementById("output");
  const status = document.getElementById("status");
  const outputLang = document.getElementById("outputLang");
  const translateBtn = document.getElementById("translateBtn");
  const copyBtn = document.getElementById("copyBtn");
  const resultPanel = document.getElementById("resultPanel");
  const tagline = document.getElementById("tagline");
  const langButtons = [...document.querySelectorAll(".lang-pill")];
  const tryLinks = [...document.querySelectorAll(".try-link")];

  const labels = { sw: "Kiswahili", kik: "Kikuyu", guz: "Ekegusii" };
  const taglines = {
    sw: "Arifa za umma — kwa Kiswahili",
    kik: "Ũhoro wa umma — kwa Gĩkũyũ",
    guz: "Amachiko a abanto — kwa Ekegusii",
  };
  let target = "sw";

  function setTagline() {
    tagline.textContent = taglines[target] || taglines.sw;
  }

  function clearStatus() {
    status.hidden = true;
    status.textContent = "";
    status.classList.remove("error");
  }

  function showError(msg) {
    resultPanel.hidden = false;
    output.textContent = "";
    status.hidden = false;
    status.textContent = msg || "Something went wrong.";
    status.classList.add("error");
  }

  langButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      target = btn.dataset.target;
      langButtons.forEach((b) => b.classList.toggle("active", b === btn));
      outputLang.textContent = labels[target];
      setTagline();
    });
  });

  tryLinks.forEach((btn) => {
    btn.addEventListener("click", () => {
      source.value = btn.dataset.example || "";
      source.focus();
    });
  });

  copyBtn.addEventListener("click", async () => {
    const text = output.textContent.trim();
    if (!text) return;
    const prev = copyBtn.textContent;
    try {
      await navigator.clipboard.writeText(text);
      copyBtn.textContent = "Copied";
      setTimeout(() => {
        copyBtn.textContent = prev;
      }, 1200);
    } catch {
      showError("Could not copy.");
    }
  });

  async function translate(event) {
    if (event) event.preventDefault();
    const text = source.value.trim();
    if (!text) {
      showError("Type an English PSA first.");
      return;
    }

    translateBtn.disabled = true;
    translateBtn.classList.add("busy");
    clearStatus();
    // Keep last good result visible; don't flash "Translating…"
    resultPanel.hidden = resultPanel.hidden;

    try {
      const res = await fetch("/translate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, target }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data.detail;
        const msg = typeof detail === "string" ? detail : `Request failed (${res.status})`;
        throw new Error(msg);
      }
      resultPanel.hidden = false;
      outputLang.textContent = labels[target];
      output.textContent = data.translation || "";
      clearStatus();
    } catch (err) {
      showError(err.message || String(err));
    } finally {
      translateBtn.disabled = false;
      translateBtn.classList.remove("busy");
    }
  }

  form.addEventListener("submit", translate);
  setTagline();
})();
