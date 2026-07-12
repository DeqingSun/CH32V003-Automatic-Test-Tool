/* global MatrixView */
const MatrixView = (() => {
  let pins = null;
  let connections = [];
  let selectedX = null;
  let selectedY = null;
  let onChange = null;
  /** pin 0..7 → { kind: null|'square'|'circle', high: boolean } */
  const pinIo = Array.from({ length: 8 }, () => ({ kind: null, high: false }));

  /** Distinct from signal pins and from network palette. */
  const POWER_CLASS = { VSS: "power-vss", VDD: "power-vdd" };

  /* Avoid VSS slate / VDD amber so rail base colors stay recognizable. */
  const NET_PALETTE = [
    "#3db8a8",
    "#61afef",
    "#c678dd",
    "#e06c75",
    "#98c379",
    "#e5c07b",
    "#56b6c2",
    "#d19a66",
    "#7dce82",
    "#c49a6c",
  ];

  function setPins(data) {
    pins = data;
  }

  function setConnections(list) {
    connections = list || [];
    renderHighlights();
    renderList();
  }

  function getSelection() {
    return { x: selectedX, y: selectedY };
  }

  function findParent(parent, x) {
    if (parent.get(x) !== x) {
      parent.set(x, findParent(parent, parent.get(x)));
    }
    return parent.get(x);
  }

  function union(parent, a, b) {
    const ra = findParent(parent, a);
    const rb = findParent(parent, b);
    if (ra !== rb) parent.set(ra, rb);
  }

  /** Map net name → palette color for its connected component. */
  function netColorMap() {
    const parent = new Map();
    for (const c of connections) {
      if (!parent.has(c.x_name)) parent.set(c.x_name, c.x_name);
      if (!parent.has(c.y_name)) parent.set(c.y_name, c.y_name);
      union(parent, c.x_name, c.y_name);
    }
    const rootIndex = new Map();
    let next = 0;
    const colors = new Map();
    for (const name of parent.keys()) {
      const root = findParent(parent, name);
      if (!rootIndex.has(root)) {
        rootIndex.set(root, next++);
      }
      colors.set(name, NET_PALETTE[rootIndex.get(root) % NET_PALETTE.length]);
    }
    return colors;
  }

  function colorForConnection(c, colors) {
    return colors.get(c.y_name) || colors.get(c.x_name) || NET_PALETTE[0];
  }

  function hexToRgba(hex, alpha) {
    const h = hex.replace("#", "");
    const r = parseInt(h.slice(0, 2), 16);
    const g = parseInt(h.slice(2, 4), 16);
    const b = parseInt(h.slice(4, 6), 16);
    return `rgba(${r},${g},${b},${alpha})`;
  }

  function renderBoard() {
    if (!pins) return;
    const ssop = document.getElementById("ssop");
    ssop.innerHTML = "";
    const body = document.createElement("div");
    body.className = "ssop-body";
    ssop.appendChild(body);

    for (let i = 0; i < 10; i++) {
      const left = pins.dut_left[i];
      const right = pins.dut_right[i];
      const lbtn = makePinButton(left.name, left.pin, false);
      const rbtn = makePinButton(right.name, right.pin, true);
      lbtn.style.gridColumn = "1";
      lbtn.style.gridRow = String(i + 1);
      rbtn.style.gridColumn = "3";
      rbtn.style.gridRow = String(i + 1);
      ssop.appendChild(lbtn);
      ssop.appendChild(rbtn);
    }

    fillNetList("probe-nets", pins.probe, "x");
    fillNetList("y-nets", pins.controller_y, "y");
    bindClearOnEmptyClick();
    renderHighlights();
  }

  function makePinButton(name, pinNum, right) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "pin-btn" + (right ? " right" : "");
    btn.dataset.net = name;
    btn.dataset.side = "x";
    if (POWER_CLASS[name]) {
      btn.classList.add("power", POWER_CLASS[name]);
      btn.textContent = right ? `${name} ${pinNum}` : `${pinNum} ${name}`;
      btn.disabled = true;
      btn.title = `${name} (not selectable)`;
      return btn;
    }
    btn.textContent = right ? `${name} ${pinNum}` : `${pinNum} ${name}`;
    btn.addEventListener("click", () => selectX(name));
    return btn;
  }

  function shortLabel(name) {
    if (name.startsWith("305_")) return name.slice(4);
    if (name.startsWith("WCH_LINKE_")) return name.slice(10);
    return name;
  }

  function paIndexFromYName(name) {
    const m = /^305_PA(\d)$/.exec(name);
    return m ? Number(m[1]) : null;
  }

  function fillNetList(id, names, side) {
    const el = document.getElementById(id);
    el.innerHTML = "";
    for (const name of names) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "net-btn";
      btn.dataset.net = name;
      btn.dataset.side = side;
      btn.title = name;
      const label = document.createElement("span");
      label.className = "net-label";
      label.textContent = shortLabel(name);
      btn.appendChild(label);
      if (side === "y") {
        const pa = paIndexFromYName(name);
        if (pa !== null) {
          btn.dataset.pa = String(pa);
          const mark = document.createElement("span");
          mark.className = "io-mark";
          mark.setAttribute("aria-hidden", "true");
          btn.appendChild(mark);
        }
      }
      btn.addEventListener("click", () => {
        if (side === "x") selectX(name);
        else selectY(name);
      });
      el.appendChild(btn);
    }
    if (side === "y") applyPinIoMarks();
  }

  function applyPinIoMarks() {
    document.querySelectorAll("#y-nets .net-btn[data-pa]").forEach((btn) => {
      const pa = Number(btn.dataset.pa);
      const mark = btn.querySelector(".io-mark");
      if (!mark || pa < 0 || pa > 7) return;
      const st = pinIo[pa];
      mark.className = "io-mark";
      if (!st.kind) return;
      mark.classList.add(st.kind, st.high ? "high" : "low");
    });
  }

  /** @param {number} pin 0..7 @param {'square'|'circle'|null} kind @param {boolean} [high] */
  function setPinIoState(pin, kind, high) {
    if (pin < 0 || pin > 7) return;
    pinIo[pin] = { kind: kind || null, high: !!high };
    applyPinIoMarks();
  }

  /** Update circle levels for multiple pins without changing square/output kinds. */
  function setPinLevels(levels) {
    for (const [key, high] of Object.entries(levels || {})) {
      const pin = Number(key);
      if (pin < 0 || pin > 7) continue;
      if (pinIo[pin].kind === "circle") {
        pinIo[pin].high = !!high;
      }
    }
    applyPinIoMarks();
  }

  function clearPinIoStates() {
    for (let i = 0; i < 8; i++) {
      pinIo[i] = { kind: null, high: false };
    }
    applyPinIoMarks();
  }

  function selectX(name) {
    if (POWER_CLASS[name]) return;
    if (name.startsWith("WCH_LINKE_")) return;
    selectedX = name;
    document.getElementById("sel-x").textContent = name;
    renderHighlights();
    if (onChange) onChange(getSelection());
  }

  function selectY(name) {
    selectedY = name;
    document.getElementById("sel-y").textContent = name;
    renderHighlights();
    if (onChange) onChange(getSelection());
  }

  function clearSelection() {
    if (selectedX === null && selectedY === null) return;
    selectedX = null;
    selectedY = null;
    document.getElementById("sel-x").textContent = "—";
    document.getElementById("sel-y").textContent = "—";
    renderHighlights();
    if (onChange) onChange(getSelection());
  }

  function bindClearOnEmptyClick() {
    const board = document.getElementById("board-card");
    if (!board || board.dataset.clearBound === "1") return;
    board.dataset.clearBound = "1";
    board.addEventListener("click", (e) => {
      if (e.target.closest(".pin-btn, .net-btn")) return;
      clearSelection();
    });
  }

  function clearNetStyle(btn) {
    btn.classList.remove("linked");
    btn.style.borderColor = "";
    btn.style.boxShadow = "";
    btn.style.backgroundImage = "";
  }

  function renderHighlights() {
    const colors = netColorMap();
    document.querySelectorAll(".pin-btn, .net-btn").forEach((btn) => {
      const net = btn.dataset.net;
      btn.classList.toggle("selected", net === selectedX || net === selectedY);
      clearNetStyle(btn);
      const color = colors.get(net);
      if (color) {
        btn.classList.add("linked");
        btn.style.borderColor = color;
        btn.style.boxShadow = `inset 0 0 0 1px ${color}`;
        btn.style.backgroundImage = `linear-gradient(${hexToRgba(color, 0.22)}, ${hexToRgba(color, 0.22)})`;
      }
    });
  }

  function renderList() {
    const ul = document.getElementById("conn-list");
    ul.innerHTML = "";
    if (!connections.length) {
      const li = document.createElement("li");
      li.style.color = "var(--muted)";
      li.textContent = "No connections";
      ul.appendChild(li);
      return;
    }
    const colors = netColorMap();
    for (const c of connections) {
      const li = document.createElement("li");
      const color = colorForConnection(c, colors);
      li.textContent = `${c.x_name}  ↔  ${c.y_name}`;
      li.style.color = color;
      li.style.borderLeft = `3px solid ${color}`;
      li.style.paddingLeft = "0.45rem";
      ul.appendChild(li);
    }
  }

  return {
    setPins,
    setConnections,
    renderBoard,
    getSelection,
    clearSelection,
    selectX,
    selectY,
    setPinIoState,
    setPinLevels,
    clearPinIoStates,
    paIndexFromYName,
    onSelectionChange(cb) { onChange = cb; },
  };
})();
