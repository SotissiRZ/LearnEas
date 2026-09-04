(() => {
  "use strict";
  const MAX_JS_CHARS = 100000;
  const MAX_PY_FILES = 30;
  let activeWorker = null;
  let activeTimer = null;

  function finish(nonce, output) {
    if (activeTimer) clearTimeout(activeTimer);
    activeTimer = null;
    if (activeWorker) activeWorker.terminate();
    activeWorker = null;
    parent.postMessage({ source: "learneas-code-runner", nonce, output: String(output || "") }, "*");
  }

  function safePath(value) {
    return String(value || "")
      .replace(/\\/g, "/")
      .replace(/^\/+/, "")
      .split("/")
      .filter((part) => part && part !== "." && part !== "..")
      .join("/");
  }

  function runJavaScript(message) {
    const nonce = Number(message.nonce || 0);
    const code = String(message.code || "").slice(0, MAX_JS_CHARS);
    const workerSource = `
      "use strict";
      const out = [];
      const fmt = (v) => {
        try { return typeof v === "string" ? v : JSON.stringify(v); }
        catch { return String(v); }
      };
      console.log = (...a) => out.push(a.map(fmt).join(" "));
      console.info = (...a) => out.push(a.map(fmt).join(" "));
      console.warn = (...a) => out.push("Avertissement: " + a.map(fmt).join(" "));
      console.error = (...a) => out.push("Erreur: " + a.map(fmt).join(" "));
      try {
        ${code}\n
        self.postMessage({output: out.join("\\n") || "Exécution terminée sans sortie console."});
      } catch (error) {
        out.push("Erreur: " + (error && error.stack ? error.stack : String(error)));
        self.postMessage({output: out.join("\\n")});
      }
    `;
    const url = URL.createObjectURL(new Blob([workerSource], { type: "text/javascript" }));
    activeWorker = new Worker(url);
    URL.revokeObjectURL(url);
    activeWorker.onmessage = (event) => finish(nonce, event.data && event.data.output);
    activeWorker.onerror = () => finish(nonce, "Erreur JavaScript: moteur isolé indisponible.");
    activeTimer = setTimeout(() => finish(nonce, "Erreur JavaScript: délai d'exécution dépassé (10 s)."), 10000);
  }

  function runPython(message) {
    const nonce = Number(message.nonce || 0);
    const files = Array.isArray(message.files) ? message.files.slice(0, MAX_PY_FILES).map((item) => ({
      path: safePath(item && item.path),
      content: String((item && item.content) || "").slice(0, MAX_JS_CHARS),
    })).filter((item) => item.path) : [];
    const active = safePath(message.active || "main.py") || "main.py";
    const workerSource = `
      self.onmessage = async (event) => {
        try {
          importScripts("https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.js");
          const pyodide = await loadPyodide({ indexURL: "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/" });
          let output = "";
          pyodide.setStdout({ batched: (text) => { output += text + "\\n"; } });
          pyodide.setStderr({ batched: (text) => { output += "Erreur: " + text + "\\n"; } });
          const root = "/home/pyodide/learneas_project";
          pyodide.FS.mkdirTree(root);
          for (const file of event.data.files) {
            const absolute = root + "/" + file.path;
            pyodide.FS.mkdirTree(absolute.slice(0, absolute.lastIndexOf("/")));
            pyodide.FS.writeFile(absolute, String(file.content || ""), { encoding: "utf8" });
          }
          pyodide.runPython("import os,sys,importlib; os.chdir(" + JSON.stringify(root) + "); sys.path.insert(0," + JSON.stringify(root) + ") if " + JSON.stringify(root) + " not in sys.path else None; importlib.invalidate_caches()");
          await pyodide.runPythonAsync("exec(compile(open(" + JSON.stringify(event.data.active) + ").read(), " + JSON.stringify(event.data.active) + ", 'exec'))");
          self.postMessage({ output: output.trim() || "Exécution Python terminée sans sortie." });
        } catch (error) {
          self.postMessage({ output: "Erreur Python: " + (error && error.message ? error.message : String(error)) });
        }
      };
    `;
    const url = URL.createObjectURL(new Blob([workerSource], { type: "text/javascript" }));
    activeWorker = new Worker(url);
    URL.revokeObjectURL(url);
    activeWorker.onmessage = (event) => finish(nonce, event.data && event.data.output);
    activeWorker.onerror = () => finish(nonce, "Erreur Python: moteur isolé indisponible.");
    activeTimer = setTimeout(() => finish(nonce, "Erreur Python: délai d'exécution dépassé (20 s)."), 20000);
    activeWorker.postMessage({ files, active });
  }

  window.addEventListener("message", (event) => {
    if (event.source !== parent || !event.data || event.data.source !== "learneas-code-parent") return;
    if (activeWorker) activeWorker.terminate();
    if (activeTimer) clearTimeout(activeTimer);
    activeWorker = null;
    activeTimer = null;
    if (event.data.runtime === "python") runPython(event.data);
    else if (event.data.runtime === "javascript") runJavaScript(event.data);
  });
})();
