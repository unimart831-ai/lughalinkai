(() => {
  const source = document.getElementById("source");
  const form = document.getElementById("composeForm");
  const output = document.getElementById("output");
  const status = document.getElementById("status");
  const outputLang = document.getElementById("outputLang");
  const translateBtn = document.getElementById("translateBtn");
  const copyBtn = document.getElementById("copyBtn");
  const resultPanel = document.getElementById("resultPanel");
  const greeting = document.getElementById("greeting");
  const langButtons = [...document.querySelectorAll(".lang-pill")];
  const tryLinks = [...document.querySelectorAll(".try-link")];

  const labels = { sw: "Kiswahili", kik: "Kikuyu" };
  let target = "sw";

  function setGreeting() {
    const h = new Date().getHours();
    let text = "Good evening";
    if (h < 12) text = "Good morning";
    else if (h < 18) text = "Good afternoon";
    greeting.textContent = text;
  }

  function setStatus(msg, isError = false) {
    status.textContent = msg || "";
    status.classList.toggle("error", Boolean(isError && msg));
  }

  langButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      target = btn.dataset.target;
      langButtons.forEach((b) => b.classList.toggle("active", b === btn));
      outputLang.textContent = labels[target];
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
    try {
      await navigator.clipboard.writeText(text);
      setStatus("Copied.");
    } catch {
      setStatus("Could not copy.", true);
    }
  });

  async function translate(event) {
    if (event) event.preventDefault();
    const text = source.value.trim();
    if (!text) {
      resultPanel.hidden = false;
      output.textContent = "";
      setStatus("Type an English PSA first.", true);
      return;
    }

    translateBtn.disabled = true;
    resultPanel.hidden = false;
    output.textContent = "Translating…";
    setStatus("Calling Hub model on the server — nothing downloads in your browser.");

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
      output.textContent = data.translation || "";
      setStatus(data.model ? `Model · ${data.model}` : "");
    } catch (err) {
      output.textContent = "";
      setStatus(err.message || String(err), true);
    } finally {
      translateBtn.disabled = false;
    }
  }

  form.addEventListener("submit", translate);
  setGreeting();
})();
