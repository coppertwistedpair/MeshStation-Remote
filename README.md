# MeshRX

Remote receiver for [MeshStation](../MeshStation). Run this on a Raspberry Pi
(or any Linux box) with an RTL-SDR attached; it demodulates Meshtastic LoRa
frames and streams them to MeshStation over the network via ZMQ PUB, using
the exact same 0x03 frame format and demod chain as MeshStation's internal
engine.

## How it fits together

- `meshrx/flowgraphs/` — same GNU Radio flowgraph MeshStation's internal
  engine uses (RTL-SDR source -> freq xlating filter -> LoRa SDR demod chain
  -> frame aggregator that emits `0x03`-type frames with payload + SNR/RSSI).
- `meshrx/pdu_zmq_sink.py` — replaces MeshStation's internal TCP sink; binds
  a ZMQ PUB socket and publishes each frame.
- `meshrx/meshtastic_presets.py` — Meshtastic's region/modem-preset tables
  and its exact frequency-hash formula, copied from MeshStation so MeshRX
  computes the same center frequency the firmware would.
- `meshrx/setup_wizard.py` — first-time setup: pick your region + modem
  preset interactively, get the correct radio parameters, no manual lookup.
- `meshrx/run_engine.py` — CLI entry point that wires it all together.

MeshStation decrypts the Meshtastic payload itself once it receives a frame,
so **this program does not need the channel's AES key at all** — only
MeshStation's "External" connection settings do (IP, port, AES key of the
channel you want decoded).

## Install (Raspberry Pi / Linux)

GNU Radio + gr-lora_sdr + gr-osmosdr aren't pip-installable, so this reuses
MeshStation's own conda/micromamba runtime builder:

```bash
cd install/linux_aarch64   # use linux_x86_64 on an x86 Pi/Linux box
./auto-engine-builder.sh
```

This builds a self-contained `./runtime` env (same one MeshStation's
internal engine ships) with `pyzmq` added on top, then prunes it down.

You also need `librtlsdr` / USB access on the Pi (`rtl-sdr` udev rules), and
the RTL-SDR plugged in.

## Run

First run with no arguments launches the setup wizard automatically — pick
your Meshtastic region (e.g. `US`, `EU_868`) and modem preset (e.g.
`LONG_FAST`), and it computes and saves the correct center frequency,
bandwidth, spreading factor and sample rate (same formula the Meshtastic
firmware uses, including the frequency-slot hash):

```bash
cd install/linux_aarch64
./runtime/bin/python ../../meshrx.py
```

Answers are saved to `meshrx_config.json` at the repo root; every later run
reuses them automatically. Re-run the wizard any time with `--setup`, or
skip it non-interactively by passing `--region`/`--preset` directly:

```bash
./runtime/bin/python ../../meshrx.py --region US --preset LONG_FAST --port 5555
```

You can still bypass all of this and set raw radio parameters yourself:

```bash
./runtime/bin/python ../../meshrx.py \
  --center-freq 869525000 --sf 11 --lora-bw 250000 --gain 30 --port 5555
```

Precedence per run: explicit `--center-freq`/`--sf`/`--lora-bw` > computed
from `--region`/`--preset` > saved `meshrx_config.json` > wizard (if nothing
saved yet).

## Connect from MeshStation

In MeshStation: Connection Settings -> **External** tab:

- **IP Address** — the Raspberry Pi's IP on your network
- **Port** — the `--port` MeshRX was started with (default `5555`)
- **AES Key (Base64)** — the Meshtastic channel key (MeshStation-side only,
  used to decrypt payloads after receiving them — leave `AQ==` for the
  default public channel)

Then click **Connect**. MeshStation opens a ZMQ SUB socket to
`tcp://<IP>:<port>` and parses the same frame stream the internal engine
would have produced locally.

## CLI reference

| Flag | Default | Meaning |
|---|---|---|
| `--setup` | — | Run the region/preset wizard and exit |
| `--region` | — | Meshtastic region key, e.g. `US`, `EU_868` (needs `--preset`) |
| `--preset` | — | Meshtastic modem preset key, e.g. `LONG_FAST` (needs `--region`) |
| `--channel-name` | preset default | Channel name used for the frequency-slot hash |
| `--bind-host` | `0.0.0.0` | ZMQ PUB bind address |
| `--port` | `5555` | ZMQ PUB bind port |
| `--center-freq` | computed/saved | Center frequency (Hz) — overrides region/preset/config |
| `--samp-rate` | computed/saved | RTL-SDR sample rate (sps) |
| `--lora-bw` | computed/saved | LoRa bandwidth (Hz) |
| `--sf` | computed/saved | Spreading factor |
| `--gain` | `30.0` | RF gain |
| `--ppm` | `0.0` | Frequency correction (ppm) |
| `--if-gain` / `--bb-gain` | `20` / `20` | RTL-SDR IF/baseband gain |
| `--device-args` | `""` | Extra osmocom source args, e.g. `rtl=0` |
| `--bias-tee` | off | Enable bias-T / antenna power |
| `--preset-id` | `0` | Preset ID byte embedded in each frame |
| `--extra-demod-configs` | none | JSON list to demod multiple SF/BW at once, sharing the same SDR |
