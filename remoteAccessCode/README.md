# Remote Access Web UI

Python web console for the CH32V003 automatic test jig: matrix routing, controller GPIO, digital/analog capture with zoomable waveforms, and DUT firmware upload.

## Install

```bash
cd remoteAccessCode
python3 -m pip install -r requirements.txt
```

## Run

With the CH32V305 controller plugged in (USB serial number `CH32V30x`):

```bash
cd remoteAccessCode
python3 server.py
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/). Bind address is `0.0.0.0` so you can reach it from another machine on the LAN.

Optional port override:

```bash
REMOTE_ACCESS_PORT=8080 python3 server.py
```

If the controller is missing at startup, the UI shows **Disconnected** — use **Reconnect** after plugging it in.

## Features

- **Matrix** — connect/disconnect DUT / probe / LinkE nets to controller PA0–PA7; active links are tracked on the host
- **GPIO** — digital read/write and analog read/write on PA0–PA7 (DAC on PA4/PA5)
- **Capture** — digital logic analyzer or multi-channel analog capture; scroll to zoom, drag to pan
- **Firmware** — upload `.bin` / `.hex`; Python routes SWIO and flashes via on-board WCH-LinkE (`minichlink`)

No authentication in this version — use only on trusted networks.
