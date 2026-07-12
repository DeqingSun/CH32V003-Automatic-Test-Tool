/* global WaveformViewer */
const WaveformViewer = (() => {
  const COLORS = [
    "#9aa0a6",
    "#c49a6c",
    "#e06c75",
    "#e5a15c",
    "#d4c05a",
    "#7dce82",
    "#61afef",
    "#c678dd",
  ];

  const canvas = () => document.getElementById("wave-canvas");
  const emptyEl = () => document.getElementById("wave-empty");

  let data = null; // { kind, rate_hz, sample_count, channels?, samples: number[][] }
  let viewStart = 0; // sample index
  let viewEnd = 0;
  let yScale = 1;
  let yOffset = 0;
  let dragging = false;
  let lastX = 0;
  let lastY = 0;

  function setDigital(payload) {
    const bytes = Uint8Array.from(atob(payload.samples_b64), (c) => c.charCodeAt(0));
    const channels = [];
    for (let ch = 0; ch < 8; ch++) {
      const arr = new Array(bytes.length);
      for (let i = 0; i < bytes.length; i++) {
        arr[i] = (bytes[i] >> ch) & 1;
      }
      channels.push(arr);
    }
    data = {
      kind: "digital",
      rate_hz: payload.rate_hz,
      sample_count: payload.sample_count,
      channels: [...Array(8).keys()],
      samples: channels,
    };
    fit();
    emptyEl().classList.add("hidden");
    draw();
  }

  function setAnalog(payload) {
    const samples = payload.samples_b64.map((b64) => {
      const raw = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
      const view = new DataView(raw.buffer);
      const out = new Array(raw.length / 2);
      for (let i = 0; i < out.length; i++) {
        out[i] = view.getUint16(i * 2, true);
      }
      return out;
    });
    data = {
      kind: "analog",
      rate_hz: payload.rate_hz,
      sample_count: payload.sample_count,
      channels: payload.channels,
      samples,
    };
    yScale = 1;
    yOffset = 0;
    fit();
    emptyEl().classList.add("hidden");
    draw();
  }

  function fit() {
    if (!data) return;
    viewStart = 0;
    viewEnd = Math.max(1, data.sample_count);
    yScale = 1;
    yOffset = 0;
    draw();
  }

  function reset() {
    fit();
  }

  function sampleAtX(clientX) {
    const c = canvas();
    const rect = c.getBoundingClientRect();
    const x = ((clientX - rect.left) / rect.width) * c.width;
    const marginL = 56;
    const marginR = 16;
    const plotW = c.width - marginL - marginR;
    const t = (x - marginL) / plotW;
    return viewStart + t * (viewEnd - viewStart);
  }

  function zoomAt(clientX, factor) {
    if (!data) return;
    const center = sampleAtX(clientX);
    const span = viewEnd - viewStart;
    const newSpan = Math.max(8, Math.min(data.sample_count, span * factor));
    const ratio = (center - viewStart) / span;
    viewStart = center - newSpan * ratio;
    viewEnd = viewStart + newSpan;
    if (viewStart < 0) {
      viewEnd -= viewStart;
      viewStart = 0;
    }
    if (viewEnd > data.sample_count) {
      viewStart -= viewEnd - data.sample_count;
      viewEnd = data.sample_count;
      if (viewStart < 0) viewStart = 0;
    }
    draw();
  }

  function panSamples(dxPixels) {
    if (!data) return;
    const c = canvas();
    const plotW = c.width - 72;
    const span = viewEnd - viewStart;
    const delta = (-dxPixels / plotW) * span;
    let ns = viewStart + delta;
    let ne = viewEnd + delta;
    if (ns < 0) {
      ne -= ns;
      ns = 0;
    }
    if (ne > data.sample_count) {
      ns -= ne - data.sample_count;
      ne = data.sample_count;
      if (ns < 0) ns = 0;
    }
    viewStart = ns;
    viewEnd = ne;
    draw();
  }

  function formatTime(sampleIndex) {
    if (!data || !data.rate_hz) return "";
    const t = sampleIndex / data.rate_hz;
    if (t < 1e-3) return `${(t * 1e6).toFixed(2)} µs`;
    if (t < 1) return `${(t * 1e3).toFixed(3)} ms`;
    return `${t.toFixed(4)} s`;
  }

  function draw() {
    const c = canvas();
    const ctx = c.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const cssW = c.clientWidth || 1200;
    const cssH = 420;
    c.width = Math.floor(cssW * dpr);
    c.height = Math.floor(cssH * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const W = cssW;
    const H = cssH;

    ctx.fillStyle = "#0c1015";
    ctx.fillRect(0, 0, W, H);

    if (!data) return;

    const marginL = 56;
    const marginR = 16;
    const marginT = 16;
    const marginB = 28;
    const plotW = W - marginL - marginR;
    const plotH = H - marginT - marginB;
    const nCh = data.channels.length;
    const rowH = plotH / nCh;
    const span = Math.max(1, viewEnd - viewStart);

    // grid
    ctx.strokeStyle = "#1c2530";
    ctx.lineWidth = 1;
    for (let i = 0; i <= 10; i++) {
      const x = marginL + (plotW * i) / 10;
      ctx.beginPath();
      ctx.moveTo(x, marginT);
      ctx.lineTo(x, marginT + plotH);
      ctx.stroke();
    }

    ctx.fillStyle = "#8b9bb0";
    ctx.font = "11px IBM Plex Mono, monospace";
    for (let i = 0; i <= 5; i++) {
      const s = viewStart + (span * i) / 5;
      const x = marginL + (plotW * i) / 5;
      ctx.fillText(formatTime(s), x - 10, H - 8);
    }

    const i0 = Math.max(0, Math.floor(viewStart));
    const i1 = Math.min(data.sample_count - 1, Math.ceil(viewEnd));
    const step = Math.max(1, Math.floor((i1 - i0) / (plotW * 2)));

    for (let row = 0; row < nCh; row++) {
      const ch = data.channels[row];
      const samples = data.samples[row];
      const yBase = marginT + row * rowH;
      const color = COLORS[ch % COLORS.length];

      ctx.fillStyle = color;
      ctx.fillText(`PA${ch}`, 8, yBase + rowH / 2 + 4);

      ctx.strokeStyle = "#243040";
      ctx.beginPath();
      ctx.moveTo(marginL, yBase + rowH);
      ctx.lineTo(marginL + plotW, yBase + rowH);
      ctx.stroke();

      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.beginPath();

      if (data.kind === "digital") {
        const yHigh = yBase + rowH * 0.18;
        const yLow = yBase + rowH * 0.82;
        let first = true;
        let prev = null;
        for (let i = i0; i <= i1; i += step) {
          const x = marginL + ((i - viewStart) / span) * plotW;
          const y = samples[i] ? yHigh : yLow;
          if (first) {
            ctx.moveTo(x, y);
            first = false;
          } else if (prev !== samples[i]) {
            ctx.lineTo(x, prev ? yHigh : yLow);
            ctx.lineTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
          prev = samples[i];
        }
      } else {
        const mid = yBase + rowH / 2;
        const amp = (rowH * 0.4) * yScale;
        const yOfAdc = (adc) => {
          const v = (adc / 4095) * 2 - 1;
          return mid - v * amp - yOffset * rowH * 0.1;
        };
        const refs = [
          { adc: 0, label: "0V" },
          { adc: 4095, label: "3.3V" },
        ];
        for (const ref of refs) {
          const y = yOfAdc(ref.adc);
          if (y < yBase || y > yBase + rowH) continue;
          ctx.strokeStyle = "#3a4a5c";
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(marginL, y);
          ctx.lineTo(marginL + plotW, y);
          ctx.stroke();
          ctx.fillStyle = "#8b9bb0";
          ctx.fillText(ref.label, 8, y + 3);
        }

        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        let first = true;
        for (let i = i0; i <= i1; i += step) {
          const x = marginL + ((i - viewStart) / span) * plotW;
          const y = yOfAdc(samples[i]);
          if (first) {
            ctx.moveTo(x, y);
            first = false;
          } else {
            ctx.lineTo(x, y);
          }
        }
      }
      ctx.stroke();
    }

    // viewport info
    ctx.fillStyle = "#8b9bb0";
    ctx.fillText(
      `${data.kind} · ${data.sample_count} samples @ ${data.rate_hz} Hz · view ${formatTime(viewStart)} – ${formatTime(viewEnd)}`,
      marginL,
      12
    );
  }

  function bind() {
    const c = canvas();
    c.addEventListener("wheel", (e) => {
      e.preventDefault();
      const factor = e.deltaY > 0 ? 1.2 : 1 / 1.2;
      if (e.shiftKey && data && data.kind === "analog") {
        yScale = Math.max(0.25, Math.min(8, yScale * (e.deltaY > 0 ? 1 / 1.15 : 1.15)));
        draw();
      } else {
        zoomAt(e.clientX, factor);
      }
    }, { passive: false });

    c.addEventListener("mousedown", (e) => {
      dragging = true;
      lastX = e.clientX;
      lastY = e.clientY;
    });
    window.addEventListener("mouseup", () => { dragging = false; });
    window.addEventListener("mousemove", (e) => {
      if (!dragging) return;
      const dx = e.clientX - lastX;
      const dy = e.clientY - lastY;
      lastX = e.clientX;
      lastY = e.clientY;
      panSamples(dx);
      if (data && data.kind === "analog") {
        yOffset += dy * 0.02;
        draw();
      }
    });
    window.addEventListener("resize", () => draw());
  }

  return { setDigital, setAnalog, fit, reset, draw, bind };
})();
