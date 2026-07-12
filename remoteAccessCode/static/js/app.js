/* global Api, MatrixView, WaveformViewer */

(() => {
  let fwFile = null;
  let captureKind = "digital";
  let pollTimer = null;

  function toast(msg, kind = "") {
    const el = document.getElementById("toast");
    el.textContent = msg;
    el.className = "toast" + (kind ? ` ${kind}` : "");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.add("hidden"), 3500);
  }

  function setMode(mode) {
    document.querySelectorAll(".mode").forEach((b) => {
      b.classList.toggle("active", b.dataset.mode === mode);
    });
    ["matrix", "gpio", "capture", "firmware"].forEach((m) => {
      document.getElementById(`panel-${m}`).classList.toggle("hidden", m !== mode);
    });
  }

  async function refreshStatus() {
    try {
      const st = await Api.get("/api/status");
      const pill = document.getElementById("conn-indicator");
      const busy = document.getElementById("busy-label");
      if (!st.connected) {
        pill.className = "conn-pill offline";
        pill.textContent = "Disconnected";
      } else if (st.busy && st.busy !== "idle") {
        pill.className = "conn-pill busy";
        pill.textContent = `Busy: ${st.busy}`;
      } else {
        pill.className = "conn-pill online";
        pill.textContent = st.port ? `Online · ${st.port}` : "Online";
      }
      busy.textContent = st.busy && st.busy !== "idle" ? `Busy: ${st.busy}` : "";
      return st;
    } catch (e) {
      document.getElementById("conn-indicator").className = "conn-pill offline";
      document.getElementById("conn-indicator").textContent = "Server error";
      return null;
    }
  }

  async function refreshMatrix() {
    const state = await Api.get("/api/matrix/state");
    MatrixView.setConnections(state.connections);
  }

  async function boot() {
    WaveformViewer.bind();
    const pins = await Api.get("/api/pins");
    MatrixView.setPins(pins);
    MatrixView.renderBoard();

    const gpioSel = document.getElementById("gpio-pin");
    gpioSel.innerHTML = "";
    for (let i = 0; i < 8; i++) {
      const opt = document.createElement("option");
      opt.value = String(i);
      opt.textContent = `PA${i}${i === 4 || i === 5 ? " (DAC)" : ""}`;
      gpioSel.appendChild(opt);
    }

    const chGrid = document.getElementById("an-channels");
    chGrid.innerHTML = "";
    for (let i = 0; i < 8; i++) {
      const label = document.createElement("label");
      /* Default PA7 — matches common blink / SWIO Y pin in this jig. */
      label.innerHTML = `<input type="checkbox" value="${i}" ${i === 7 ? "checked" : ""} /> PA${i}`;
      chGrid.appendChild(label);
    }

    await refreshStatus();
    try {
      await refreshMatrix();
    } catch {
      /* disconnected */
    }

    setInterval(refreshStatus, 2000);
  }

  document.getElementById("mode-nav").addEventListener("click", (e) => {
    const btn = e.target.closest(".mode");
    if (btn) setMode(btn.dataset.mode);
  });

  document.querySelector(".tabs").addEventListener("click", (e) => {
    const tab = e.target.closest(".tab");
    if (!tab) return;
    captureKind = tab.dataset.cap;
    document.querySelectorAll(".tab").forEach((t) => {
      t.classList.toggle("active", t.dataset.cap === captureKind);
    });
    document.getElementById("cap-digital").classList.toggle("hidden", captureKind !== "digital");
    document.getElementById("cap-analog").classList.toggle("hidden", captureKind !== "analog");
  });

  document.getElementById("btn-reconnect").addEventListener("click", async () => {
    try {
      await Api.post("/api/reconnect", {});
      toast("Controller connected", "ok");
      await refreshStatus();
      await refreshMatrix();
    } catch (e) {
      toast(e.message, "error");
    }
  });

  document.getElementById("btn-init").addEventListener("click", async () => {
    try {
      await Api.post("/api/init", {});
      MatrixView.setConnections([]);
      toast("Matrix reset", "ok");
    } catch (e) {
      toast(e.message, "error");
    }
  });

  document.getElementById("btn-connect").addEventListener("click", async () => {
    const { x, y } = MatrixView.getSelection();
    if (!x || !y) {
      toast("Select X and Y nets first", "error");
      return;
    }
    try {
      const res = await Api.post("/api/matrix/connect", { x_name: x, y_name: y });
      MatrixView.setConnections(res.connections);
      toast(`Connected ${x} ↔ ${y}`, "ok");
    } catch (e) {
      toast(e.message, "error");
    }
  });

  document.getElementById("btn-disconnect").addEventListener("click", async () => {
    const { x, y } = MatrixView.getSelection();
    if (!x || !y) {
      toast("Select X and Y nets first", "error");
      return;
    }
    try {
      const res = await Api.post("/api/matrix/disconnect", { x_name: x, y_name: y });
      MatrixView.setConnections(res.connections);
      toast(`Disconnected ${x} ↔ ${y}`, "ok");
    } catch (e) {
      toast(e.message, "error");
    }
  });

  function gpioPin() {
    return Number(document.getElementById("gpio-pin").value);
  }

  document.getElementById("btn-dig-high").addEventListener("click", async () => {
    try {
      await Api.post("/api/gpio/digital_write", { pin: gpioPin(), value: true });
      document.getElementById("gpio-result").textContent = `PA${gpioPin()} = HIGH`;
    } catch (e) {
      toast(e.message, "error");
    }
  });

  document.getElementById("btn-dig-low").addEventListener("click", async () => {
    try {
      await Api.post("/api/gpio/digital_write", { pin: gpioPin(), value: false });
      document.getElementById("gpio-result").textContent = `PA${gpioPin()} = LOW`;
    } catch (e) {
      toast(e.message, "error");
    }
  });

  document.getElementById("btn-dig-read").addEventListener("click", async () => {
    try {
      const res = await Api.post("/api/gpio/digital_read", { pin: gpioPin() });
      document.getElementById("gpio-result").textContent =
        `PA${res.pin} digital = ${res.value ? "HIGH" : "LOW"} (mode unchanged)`;
    } catch (e) {
      toast(e.message, "error");
    }
  });

  document.getElementById("btn-pin-input").addEventListener("click", async () => {
    try {
      await Api.post("/api/gpio/pin_input", { pin: gpioPin() });
      document.getElementById("gpio-result").textContent =
        `PA${gpioPin()} = INPUT (Hi-Z)`;
    } catch (e) {
      toast(e.message, "error");
    }
  });

  document.getElementById("btn-ana-write").addEventListener("click", async () => {
    const value = Number(document.getElementById("analog-value").value);
    try {
      await Api.post("/api/gpio/analog_write", { pin: gpioPin(), value });
      document.getElementById("gpio-result").textContent = `PA${gpioPin()} analog write ${value}`;
    } catch (e) {
      toast(e.message, "error");
    }
  });

  document.getElementById("btn-ana-read").addEventListener("click", async () => {
    try {
      const res = await Api.post("/api/gpio/analog_read", { pin: gpioPin() });
      document.getElementById("gpio-result").textContent = `PA${res.pin} ADC = ${res.value}`;
    } catch (e) {
      toast(e.message, "error");
    }
  });

  function watchCapture(wsPath, statusPath, resultPath, applyResult) {
    const statusEl = document.getElementById("capture-status");
    statusEl.textContent = "Starting…";
    let ws;
    try {
      ws = new WebSocket(Api.wsUrl(wsPath));
    } catch {
      ws = null;
    }

    if (ws) {
      ws.onmessage = (ev) => {
        const msg = JSON.parse(ev.data);
        if (msg.type === "status") {
          statusEl.textContent = `State: ${msg.status.state || "?"}`;
        } else if (msg.type === "done") {
          statusEl.textContent = `Done · ${msg.result.sample_count} samples @ ${msg.result.rate_hz} Hz`;
          applyResult(msg.result);
          toast("Capture complete", "ok");
          ws.close();
        } else if (msg.type === "error") {
          statusEl.textContent = `Error: ${msg.error}`;
          toast(msg.error, "error");
          ws.close();
        }
      };
      ws.onerror = () => {
        /* fall back to polling */
      };
    }

    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(async () => {
      try {
        const st = await Api.get(statusPath);
        statusEl.textContent = `State: ${st.state}${st.error ? " · " + st.error : ""}`;
        if (st.state === "done") {
          clearInterval(pollTimer);
          pollTimer = null;
          const result = await Api.get(resultPath);
          applyResult(result);
          toast("Capture complete", "ok");
          if (ws && ws.readyState === WebSocket.OPEN) ws.close();
        } else if (st.state === "error") {
          clearInterval(pollTimer);
          pollTimer = null;
          toast(st.error || "Capture failed", "error");
        }
      } catch (e) {
        /* ignore transient */
      }
    }, 300);
  }

  document.getElementById("btn-la-start").addEventListener("click", async () => {
    const rate_hz = Number(document.getElementById("la-rate").value);
    const sample_count = Number(document.getElementById("la-count").value);
    try {
      await Api.post("/api/la/start", { rate_hz, sample_count });
      watchCapture("/ws/la", "/api/la/status", "/api/la/result", (r) => {
        WaveformViewer.setDigital(r);
      });
    } catch (e) {
      toast(e.message, "error");
    }
  });

  document.getElementById("btn-an-start").addEventListener("click", async () => {
    const rate_hz = Number(document.getElementById("an-rate").value);
    const sample_count = Number(document.getElementById("an-count").value);
    let channel_mask = 0;
    document.querySelectorAll("#an-channels input:checked").forEach((cb) => {
      channel_mask |= 1 << Number(cb.value);
    });
    if (!channel_mask) {
      toast("Select at least one channel", "error");
      return;
    }
    try {
      await Api.post("/api/analog/start", { rate_hz, sample_count, channel_mask });
      watchCapture("/ws/analog", "/api/analog/status", "/api/analog/result", (r) => {
        WaveformViewer.setAnalog(r);
      });
    } catch (e) {
      toast(e.message, "error");
    }
  });

  document.getElementById("btn-fit").addEventListener("click", () => WaveformViewer.fit());
  document.getElementById("btn-reset-view").addEventListener("click", () => WaveformViewer.reset());

  function setFirmwareFile(file) {
    fwFile = file;
    document.getElementById("fw-name").textContent = file ? file.name : "No file selected";
    document.getElementById("btn-flash").disabled = !file;
  }

  document.getElementById("fw-file").addEventListener("change", (e) => {
    setFirmwareFile(e.target.files[0] || null);
  });

  const dropzone = document.getElementById("dropzone");
  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("drag");
  });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag"));
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("drag");
    const file = e.dataTransfer.files[0];
    if (file) setFirmwareFile(file);
  });

  document.getElementById("btn-flash").addEventListener("click", async () => {
    if (!fwFile) return;
    const status = document.getElementById("fw-status");
    status.textContent = "Flashing… this may take a few seconds";
    const fd = new FormData();
    fd.append("file", fwFile, fwFile.name);
    try {
      const res = await Api.upload("/api/firmware/upload", fd);
      status.textContent = `Flashed OK: ${res.filename}`;
      toast("Firmware flashed", "ok");
      await refreshMatrix();
    } catch (e) {
      status.textContent = `Failed: ${e.message}`;
      toast(e.message, "error");
    }
  });

  boot().catch((e) => toast(e.message, "error"));
})();
