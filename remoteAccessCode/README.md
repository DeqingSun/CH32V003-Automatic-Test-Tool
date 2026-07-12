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

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/). Bind address is `0.0.0.0` so you can reach it from another machine on the LAN (or via a tunnel).

Optional port override:

```bash
REMOTE_ACCESS_PORT=8080 python3 server.py
```

If the controller is missing at startup, the UI shows **Disconnected** — use **Reconnect** after plugging it in.

## Access queue (shared / internet use)

There is **no login**. Each browser gets a `jig_client` cookie. The first visitor to claim becomes the **holder** and can control the jig; others join a FIFO **wait queue**.

| Situation | Behavior |
|-----------|----------|
| Alone (no waiters) | Holder keeps control until they leave or close the tab |
| Others waiting | Holder is limited to **60 seconds**, then control passes to the next waiter |
| Holder closes tab | `leave` is sent immediately (`sendBeacon`) and the queue advances |
| Crash / no leave | Stale clients are dropped after ~15s without heartbeat |

Waiters see their position and queue length (e.g. “You are #2 of 5 waiting”). Closing the tab or clicking **Leave** releases your spot.

Environment knobs:

```bash
ACCESS_SLOT_SEC=60                 # control time when queue is non-empty
ACCESS_HEARTBEAT_TIMEOUT_SEC=15    # drop clients that stop heartbeating
```

Anyone with the URL can claim a slot — there is still **no authentication**. Prefer a tunnel with an extra gate (or private URL) if you expose this beyond a trusted group.

## Features

- **Matrix** — connect/disconnect DUT / probe nets to controller PA0–PA7; active links are tracked on the host
- **GPIO** — digital read/write and analog read/write on PA0–PA7 (DAC on PA4/PA5)
- **Capture** — digital logic analyzer or multi-channel analog capture; scroll to zoom, drag to pan
- **Firmware** — upload `.bin` / `.hex` or pick a bundled sample; Python routes SWIO and flashes via on-board WCH-LinkE (`minichlink`)
