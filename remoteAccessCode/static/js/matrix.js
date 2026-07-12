/* global MatrixView */
const MatrixView = (() => {
  let pins = null;
  let connections = [];
  let selectedX = null;
  let selectedY = null;
  let onChange = null;

  const POWER = new Set(["VSS", "VDD"]);

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

  function linkedNames() {
    const set = new Set();
    for (const c of connections) {
      set.add(c.x_name);
      set.add(c.y_name);
    }
    return set;
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
    fillNetList("linke-nets", pins.linke, "x");
    fillNetList("y-nets", pins.controller_y, "y");
    renderHighlights();
  }

  function makePinButton(name, pinNum, right) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "pin-btn" + (right ? " right" : "");
    btn.dataset.net = name;
    btn.dataset.side = "x";
    if (POWER.has(name)) {
      btn.classList.add("power");
      btn.textContent = right ? `${name} ${pinNum}` : `${pinNum} ${name}`;
      return btn;
    }
    btn.textContent = right ? `${name} ${pinNum}` : `${pinNum} ${name}`;
    btn.addEventListener("click", () => selectX(name));
    return btn;
  }

  function shortLabel(name) {
    if (name.startsWith("305_")) return name.slice(4); // PA0
    if (name.startsWith("WCH_LINKE_")) return name.slice(10); // SWDIO
    return name;
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
      btn.textContent = shortLabel(name);
      btn.addEventListener("click", () => {
        if (side === "x") selectX(name);
        else selectY(name);
      });
      el.appendChild(btn);
    }
  }

  function selectX(name) {
    if (POWER.has(name)) return;
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

  function renderHighlights() {
    const linked = linkedNames();
    document.querySelectorAll(".pin-btn, .net-btn").forEach((btn) => {
      const net = btn.dataset.net;
      btn.classList.toggle("selected", net === selectedX || net === selectedY);
      btn.classList.toggle("linked", linked.has(net));
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
    for (const c of connections) {
      const li = document.createElement("li");
      li.textContent = `${c.x_name}  ↔  ${c.y_name}`;
      ul.appendChild(li);
    }
  }

  return {
    setPins,
    setConnections,
    renderBoard,
    getSelection,
    selectX,
    selectY,
    onSelectionChange(cb) { onChange = cb; },
  };
})();
