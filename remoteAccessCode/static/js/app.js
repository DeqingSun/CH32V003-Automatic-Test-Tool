/* global Api, MatrixView, WaveformViewer */

(() => {
  let fwFile = null;
  let captureKind = "digital";
  let pollTimer = null;
  let ioPollTimer = null;
  let accessHeartbeatTimer = null;
  let lastBusy = "idle";
  let matrixConnections = [];
  /** @type {{role:string, position:number|null, queue_length:number, seconds_left:number|null, slot_sec:number}|null} */
  let accessState = null;

  /** @type {(null|'output'|'input')[]} */
  const pinMode = Array(8).fill(null);
  /** @type {boolean[]} */
  const pinOutValue = Array(8).fill(false);

  function toast(msg, kind = "") {
    const el = document.getElementById("toast");
    el.textContent = msg;
    el.className = "toast" + (kind ? ` ${kind}` : "");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.add("hidden"), 3500);
  }

  function isHolder() {
    return accessState && accessState.role === "holder";
  }

  function applyAccessState(info) {
    if (!info) return;
    accessState = info;
    const label = document.getElementById("access-label");
    const overlay = document.getElementById("access-overlay");
    const waitMsg = document.getElementById("access-wait-msg");
    const leaveBtn = document.getElementById("btn-leave");

    if (info.role === "holder") {
      overlay.classList.add("hidden");
      label.className = "access-pill holder";
      if (info.seconds_left != null) {
        label.textContent = `Control: ${info.seconds_left}s left · ${info.queue_length} waiting`;
      } else {
        label.textContent = "You have control";
      }
      leaveBtn.disabled = false;
    } else if (info.role === "waiting") {
      overlay.classList.remove("hidden");
      label.className = "access-pill waiting";
      const pos = info.position || "?";
      const total = info.queue_length || 0;
      label.textContent = `Waiting #${pos} of ${total}`;
      waitMsg.textContent = `You are #${pos} of ${total} waiting`;
      leaveBtn.disabled = false;
    } else {
      overlay.classList.remove("hidden");
      label.className = "access-pill";
      label.textContent = "No access";
      waitMsg.textContent = "Claiming a spot in the queue…";
      leaveBtn.disabled = true;
    }
  }

  async function claimAccess() {
    const res = await Api.post("/api/access/claim", {});
    applyAccessState(res.access);
    return res.access;
  }

  async function heartbeatAccess() {
    try {
      const res = await Api.post("/api/access/heartbeat", {});
      applyAccessState(res.access);
      return res.access;
    } catch {
      return null;
    }
  }

  function leaveAccessBeacon() {
    try {
      navigator.sendBeacon("/api/access/leave");
    } catch {
      /* ignore */
    }
  }

  async function leaveAccess() {
    try {
      const res = await Api.post("/api/access/leave", {});
      applyAccessState(res.access || { role: "none", position: null, queue_length: 0, seconds_left: null, slot_sec: 60 });
    } catch {
      leaveAccessBeacon();
    }
  }

  function setMode(mode) {
    document.querySelectorAll(".mode").forEach((b) => {
      b.classList.toggle("active", b.dataset.mode === mode);
    });
    ["matrix", "gpio", "capture", "firmware"].forEach((m) => {
      document.getElementById(`panel-${m}`).classList.toggle("hidden", m !== mode);
    });
  }

  function syncPinIoMarkers(hideCircles) {
    for (let pin = 0; pin < 8; pin++) {
      if (pinMode[pin] === "output") {
        MatrixView.setPinIoState(pin, "square", pinOutValue[pin]);
      } else if (!hideCircles && pinMode[pin] !== "output") {
        /* circle state applied by poll; clear if not connected */
        const connected = matrixConnections.some(
          (c) => MatrixView.paIndexFromYName(c.y_name) === pin
        );
        if (!connected) {
          MatrixView.setPinIoState(pin, null, false);
        }
      } else {
        /* busy: hide circles, keep squares already set above */
        if (pinMode[pin] !== "output") {
          MatrixView.setPinIoState(pin, null, false);
        }
      }
    }
  }

  function setPinOutput(pin, value) {
    pinMode[pin] = "output";
    pinOutValue[pin] = !!value;
    MatrixView.setPinIoState(pin, "square", pinOutValue[pin]);
  }

  function setPinInput(pin) {
    pinMode[pin] = "input";
    pinOutValue[pin] = false;
    MatrixView.setPinIoState(pin, null, false);
  }

  function clearAllPinModes() {
    for (let i = 0; i < 8; i++) {
      pinMode[i] = "input";
      pinOutValue[i] = false;
    }
    MatrixView.clearPinIoStates();
  }

  function clearAnalogChannels(channelMask) {
    for (let i = 0; i < 8; i++) {
      if (channelMask & (1 << i)) {
        pinMode[i] = "input";
        pinOutValue[i] = false;
        MatrixView.setPinIoState(i, null, false);
      }
    }
  }

  async function refreshStatus() {
    try {
      const st = await Api.get("/api/status");
      const pill = document.getElementById("conn-indicator");
      const busy = document.getElementById("busy-label");
      if (st.access) applyAccessState(st.access);
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
      lastBusy = st.busy || "idle";
      if (lastBusy !== "idle") {
        syncPinIoMarkers(true);
      }
      return st;
    } catch (e) {
      document.getElementById("conn-indicator").className = "conn-pill offline";
      document.getElementById("conn-indicator").textContent = "Server error";
      return null;
    }
  }

  async function refreshMatrix() {
    const state = await Api.get("/api/matrix/state");
    matrixConnections = state.connections || [];
    MatrixView.setConnections(matrixConnections);
    syncPinIoMarkers(lastBusy !== "idle");
  }

  function connectedInputPins() {
    const pins = [];
    const seen = new Set();
    for (const c of matrixConnections) {
      const pa = MatrixView.paIndexFromYName(c.y_name);
      if (pa === null || seen.has(pa)) continue;
      if (pinMode[pa] === "output") continue;
      seen.add(pa);
      pins.push(pa);
    }
    return pins;
  }

  const IO_POLL_INTERVAL_MS = 100;
  const IO_POLL_TIMEOUT_MS = 2000;

  async function pollPinLevels() {
    if (!isHolder()) return;
    if (lastBusy !== "idle") {
      syncPinIoMarkers(true);
      return;
    }
    const pins = connectedInputPins();
    if (!pins.length) {
      syncPinIoMarkers(false);
      return;
    }
    try {
      const st = await Api.get("/api/status", { timeout: IO_POLL_TIMEOUT_MS });
      if (st && st.access) applyAccessState(st.access);
      if (!st || !st.connected || (st.busy && st.busy !== "idle")) {
        lastBusy = (st && st.busy) || "idle";
        syncPinIoMarkers(true);
        return;
      }
      lastBusy = "idle";
      const res = await Api.post("/api/gpio/digital_read_many", { pins }, { timeout: IO_POLL_TIMEOUT_MS });
      for (const pin of pins) {
        if (pinMode[pin] === "output") continue;
        const high = !!(res.values && res.values[String(pin)]);
        MatrixView.setPinIoState(pin, "circle", high);
      }
      /* clear circles on disconnected non-output pins */
      for (let i = 0; i < 8; i++) {
        if (pinMode[i] === "output") continue;
        if (!pins.includes(i)) {
          MatrixView.setPinIoState(i, null, false);
        }
      }
    } catch (e) {
      if (e && e.status === 423) {
        await heartbeatAccess();
      }
      /* ignore transient poll errors (busy race, disconnect, timeout) */
    }
  }

  function scheduleIoPoll() {
    if (ioPollTimer) clearTimeout(ioPollTimer);
    ioPollTimer = setTimeout(async () => {
      await pollPinLevels();
      scheduleIoPoll();
    }, IO_POLL_INTERVAL_MS);
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

    await claimAccess();
    await refreshStatus();
    try {
      await refreshMatrix();
    } catch {
      /* disconnected */
    }
    await loadFirmwareSamples();

    setInterval(refreshStatus, 2000);
    if (accessHeartbeatTimer) clearInterval(accessHeartbeatTimer);
    accessHeartbeatTimer = setInterval(heartbeatAccess, 3000);
    scheduleIoPoll();
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

  document.getElementById("btn-leave").addEventListener("click", async () => {
    await leaveAccess();
    toast("Left the queue", "ok");
    await claimAccess();
  });

  window.addEventListener("pagehide", leaveAccessBeacon);
  window.addEventListener("beforeunload", leaveAccessBeacon);

  async function handleControlError(e) {
    if (e && e.status === 423) {
      await heartbeatAccess();
      const detail = (e.data && e.data.detail) || e.message;
      if (detail === "expired") {
        toast("Your control time expired", "error");
      } else if (detail === "waiting") {
        toast("Waiting in queue — no control yet", "error");
      } else {
        toast("You do not have control", "error");
      }
      return;
    }
    toast(e.message, "error");
  }

  document.getElementById("btn-reconnect").addEventListener("click", async () => {
    try {
      await Api.post("/api/reconnect", {});
      toast("Controller connected", "ok");
      await refreshStatus();
      await refreshMatrix();
    } catch (e) {
      await handleControlError(e);
    }
  });

  document.getElementById("btn-init").addEventListener("click", async () => {
    try {
      await Api.post("/api/init", {});
      matrixConnections = [];
      MatrixView.setConnections([]);
      clearAllPinModes();
      toast("Matrix reset", "ok");
    } catch (e) {
      await handleControlError(e);
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
      matrixConnections = res.connections || [];
      MatrixView.setConnections(matrixConnections);
      toast(`Connected ${x} ↔ ${y}`, "ok");
    } catch (e) {
      await handleControlError(e);
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
      matrixConnections = res.connections || [];
      MatrixView.setConnections(matrixConnections);
      syncPinIoMarkers(lastBusy !== "idle");
      toast(`Disconnected ${x} ↔ ${y}`, "ok");
    } catch (e) {
      await handleControlError(e);
    }
  });

  function gpioPin() {
    return Number(document.getElementById("gpio-pin").value);
  }

  document.getElementById("btn-dig-high").addEventListener("click", async () => {
    try {
      const pin = gpioPin();
      await Api.post("/api/gpio/digital_write", { pin, value: true });
      setPinOutput(pin, true);
      document.getElementById("gpio-result").textContent = `PA${pin} = HIGH`;
    } catch (e) {
      await handleControlError(e);
    }
  });

  document.getElementById("btn-dig-low").addEventListener("click", async () => {
    try {
      const pin = gpioPin();
      await Api.post("/api/gpio/digital_write", { pin, value: false });
      setPinOutput(pin, false);
      document.getElementById("gpio-result").textContent = `PA${pin} = LOW`;
    } catch (e) {
      await handleControlError(e);
    }
  });

  document.getElementById("btn-dig-read").addEventListener("click", async () => {
    try {
      const res = await Api.post("/api/gpio/digital_read", { pin: gpioPin() });
      document.getElementById("gpio-result").textContent =
        `PA${res.pin} digital = ${res.value ? "HIGH" : "LOW"} (mode unchanged)`;
    } catch (e) {
      await handleControlError(e);
    }
  });

  document.getElementById("btn-pin-input").addEventListener("click", async () => {
    try {
      const pin = gpioPin();
      await Api.post("/api/gpio/pin_input", { pin });
      setPinInput(pin);
      document.getElementById("gpio-result").textContent =
        `PA${pin} = INPUT (Hi-Z)`;
    } catch (e) {
      await handleControlError(e);
    }
  });

  document.getElementById("btn-ana-write").addEventListener("click", async () => {
    const value = Number(document.getElementById("analog-value").value);
    try {
      const pin = gpioPin();
      await Api.post("/api/gpio/analog_write", { pin, value });
      /* DAC drive — treat as output-ish for indicator purposes (no square; clear mode) */
      pinMode[pin] = "input";
      pinOutValue[pin] = false;
      MatrixView.setPinIoState(pin, null, false);
      document.getElementById("gpio-result").textContent = `PA${pin} analog write ${value}`;
    } catch (e) {
      await handleControlError(e);
    }
  });

  document.getElementById("btn-ana-read").addEventListener("click", async () => {
    try {
      const pin = gpioPin();
      const res = await Api.post("/api/gpio/analog_read", { pin });
      pinMode[pin] = "input";
      pinOutValue[pin] = false;
      MatrixView.setPinIoState(pin, null, false);
      document.getElementById("gpio-result").textContent = `PA${res.pin} ADC = ${res.value}`;
    } catch (e) {
      await handleControlError(e);
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
      ws.onmessage = async (ev) => {
        const msg = JSON.parse(ev.data);
        if (msg.type === "status") {
          statusEl.textContent = `State: ${msg.status.state || "?"}`;
        } else if (msg.type === "done") {
          statusEl.textContent = `Done · ${msg.result.sample_count} samples @ ${msg.result.rate_hz} Hz`;
          try {
            await applyResult(msg.result);
          } catch {
            /* ignore apply errors */
          }
          toast("Capture complete", "ok");
          lastBusy = "idle";
          ws.close();
        } else if (msg.type === "error") {
          statusEl.textContent = `Error: ${msg.error}`;
          toast(msg.error, "error");
          lastBusy = "idle";
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
          try {
            await applyResult(result);
          } catch {
            /* ignore */
          }
          toast("Capture complete", "ok");
          lastBusy = "idle";
          if (ws && ws.readyState === WebSocket.OPEN) ws.close();
        } else if (st.state === "error") {
          clearInterval(pollTimer);
          pollTimer = null;
          lastBusy = "idle";
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
      lastBusy = "la";
      syncPinIoMarkers(true);
      /* Digital LA preserves OUTPUT — keep square tracking */
      watchCapture("/ws/la", "/api/la/status", "/api/la/result", (r) => {
        WaveformViewer.setDigital(r);
      });
    } catch (e) {
      await handleControlError(e);
    }
  });

  async function restoreAnalogChannels(channelMask) {
    for (let i = 0; i < 8; i++) {
      if (!(channelMask & (1 << i))) continue;
      try {
        await Api.post("/api/gpio/pin_input", { pin: i });
        pinMode[i] = "input";
        pinOutValue[i] = false;
      } catch {
        /* ignore — firmware may already have restored INPUT */
      }
    }
  }

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
      clearAnalogChannels(channel_mask);
      lastBusy = "analog";
      syncPinIoMarkers(true);
      watchCapture("/ws/analog", "/api/analog/status", "/api/analog/result", async (r) => {
        WaveformViewer.setAnalog(r);
        await restoreAnalogChannels(channel_mask);
      });
    } catch (e) {
      await handleControlError(e);
    }
  });

  document.getElementById("btn-fit").addEventListener("click", () => WaveformViewer.fit());
  document.getElementById("btn-reset-view").addEventListener("click", () => WaveformViewer.reset());

  function setFirmwareFile(file, selectedSampleName) {
    fwFile = file;
    document.getElementById("fw-name").textContent = file ? file.name : "No file selected";
    document.getElementById("btn-flash").disabled = !file;
    const sel = document.getElementById("fw-samples");
    if (sel) {
      sel.value = selectedSampleName || "";
    }
  }

  async function loadFirmwareSamples() {
    const sel = document.getElementById("fw-samples");
    sel.innerHTML = "";
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "— Choose a sample —";
    sel.appendChild(placeholder);
    try {
      const res = await Api.get("/api/firmware/samples");
      const samples = (res && res.samples) || [];
      if (!samples.length) {
        placeholder.textContent = "No samples in sample_bin/";
        sel.disabled = true;
        return;
      }
      for (const sample of samples) {
        const opt = document.createElement("option");
        opt.value = sample.name;
        opt.textContent = sample.name.replace(/\.bin$/i, "");
        opt.dataset.url = sample.url;
        sel.appendChild(opt);
      }
      sel.disabled = false;
    } catch (e) {
      placeholder.textContent = "Could not load samples";
      sel.disabled = true;
    }
  }

  document.getElementById("fw-samples").addEventListener("change", async (e) => {
    const sel = e.target;
    const name = sel.value;
    if (!name) {
      setFirmwareFile(null, null);
      document.getElementById("fw-status").textContent = "Ready";
      return;
    }
    const opt = sel.selectedOptions[0];
    const url = opt && opt.dataset.url;
    if (!url) return;
    try {
      const r = await fetch(url);
      if (!r.ok) throw new Error(`Failed to load ${name}`);
      const blob = await r.blob();
      const file = new File([blob], name, { type: "application/octet-stream" });
      setFirmwareFile(file, name);
      document.getElementById("fw-status").textContent = `Selected sample: ${name}`;
      toast(`Selected ${name}`, "ok");
    } catch (err) {
      sel.value = "";
      setFirmwareFile(null, null);
      toast(err.message, "error");
    }
  });

  document.getElementById("fw-file").addEventListener("change", (e) => {
    setFirmwareFile(e.target.files[0] || null, null);
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
    if (file) setFirmwareFile(file, null);
  });

  document.getElementById("btn-flash").addEventListener("click", async () => {
    if (!fwFile) return;
    const status = document.getElementById("fw-status");
    status.textContent = "Flashing… this may take a few seconds";
    const fd = new FormData();
    fd.append("file", fwFile, fwFile.name);
    try {
      lastBusy = "flash";
      clearAllPinModes();
      syncPinIoMarkers(true);
      const res = await Api.upload("/api/firmware/upload", fd);
      status.textContent = `Flashed OK: ${res.filename}`;
      toast("Firmware flashed", "ok");
      lastBusy = "idle";
      await refreshMatrix();
    } catch (e) {
      status.textContent = `Failed: ${e.message}`;
      await handleControlError(e);
      lastBusy = "idle";
    }
  });

  boot().catch((e) => toast(e.message, "error"));
})();
