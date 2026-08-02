(() => {
  const source = document.getElementById("source");
  const output = document.getElementById("output");
  const status = document.getElementById("status");
  const outputLang = document.getElementById("outputLang");
  const translateBtn = document.getElementById("translateBtn");
  const copyBtn = document.getElementById("copyBtn");
  const langButtons = [...document.querySelectorAll(".lang")];
  const chips = [...document.querySelectorAll(".chip")];

  const labels = { sw: "Kiswahili", kik: "Kikuyu" };
  let target = "sw";

  function setStatus(msg, isError = false) {
    if (!msg) {
      status.hidden = true;
      status.textContent = "";
      return;
    }
    status.hidden = false;
    status.textContent = msg;
    status.classList.toggle("error", isError);
  }

  langButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      target = btn.dataset.target;
      langButtons.forEach((b) => b.classList.toggle("active", b === btn));
      outputLang.textContent = labels[target];
    });
  });

  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      source.value = chip.dataset.example || "";
      source.focus();
    });
  });

  copyBtn.addEventListener("click", async () => {
    const text = output.textContent.trim();
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setStatus("Copied.");
    } catch {
      setStatus("Could not copy.", true);
    }
  });

  async function translate() {
    const text = source.value.trim();
    if (!text) {
      setStatus("Enter an English PSA first.", true);
      return;
    }

    translateBtn.disabled = true;
    copyBtn.hidden = true;
    output.classList.add("placeholder");
    output.textContent = "Translating…";
    setStatus("Calling the server model (no download in your browser).");

    try {
      const res = await fetch("/translate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, target }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || `Request failed (${res.status})`);
      }
      output.classList.remove("placeholder");
      output.textContent = data.translation || "";
      copyBtn.hidden = !data.translation;
      setStatus(`Model: ${data.model || "hub"}`);
    } catch (err) {
      output.classList.add("placeholder");
      output.textContent = "Translation failed.";
      setStatus(err.message || String(err), true);
    } finally {
      translateBtn.disabled = false;
    }
  }

  translateBtn.addEventListener("click", translate);
  source.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") translate();
  });
})();
