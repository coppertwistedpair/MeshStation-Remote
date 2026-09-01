import argparse
import queue
import signal
import time

from .pdu_zmq_sink import PDUZMQSink
from .setup_wizard import CONFIG_PATH, load_config, run_wizard
from .meshtastic_presets import calc_freq

# Flowgraph (same demod chain / 0x03 framing as MeshStation's internal engine)
from .flowgraphs.rx_lora_base_engine import build_top_block


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="meshrx")
    ap.add_argument("--bind-host", default="0.0.0.0", help="Bind address for ZMQ PUB output")
    ap.add_argument("--port", type=int, default=5555, help="Bind port for ZMQ PUB output")

    ap.add_argument("--setup", action="store_true", default=False, help="Run the region/preset setup wizard and exit")

    # Meshtastic-aware shortcuts: computes center-freq/sf/bw for you.
    ap.add_argument("--region", default=None, help="Meshtastic region key (e.g. US, EU_868) — computes radio params")
    ap.add_argument("--preset", default=None, help="Meshtastic modem preset key (e.g. LONG_FAST)")
    ap.add_argument("--channel-name", default=None, help="Channel name used for frequency hashing (default: preset's default channel name)")

    # Raw radio parameters — override --region/--preset/saved config when given
    ap.add_argument("--center-freq", type=int, default=None, help="Center frequency (Hz)")
    ap.add_argument("--samp-rate", type=int, default=None, help="Sample rate (sps)")
    ap.add_argument("--lora-bw", type=int, default=None, help="LoRa bandwidth (Hz)")
    ap.add_argument("--sf", type=int, default=None, help="Spreading factor")

    ap.add_argument("--gain", type=float, default=30.0, help="RF gain")
    ap.add_argument("--ppm", type=float, default=0.0, help="Frequency correction (ppm)")
    ap.add_argument("--if-gain", type=int, default=20, help="IF gain")
    ap.add_argument("--bb-gain", type=int, default=20, help="Baseband gain")

    ap.add_argument("--device-args", default="", help="Osmocom source args (e.g. 'rtl=0')")
    ap.add_argument("--bias-tee", action="store_true", default=False, help="Enable bias-T / antenna power")
    ap.add_argument("--payload-wait-ms", type=int, default=None, help="Override aggregator payload_wait_ms")
    ap.add_argument("--metrics-ttl-ms", type=int, default=None, help="Override aggregator metrics_ttl_ms")
    ap.add_argument("--preset-id", type=int, default=0, help="Preset ID byte embedded in each frame (0=unset)")
    ap.add_argument("--extra-demod-configs", default=None, help="JSON list of extra demod chains, e.g. '[{\"sf\":9,\"bw\":250000,...}]'")

    args = ap.parse_args(argv)

    if args.setup:
        run_wizard()
        return 0

    center_freq, samp_rate, lora_bw, sf = args.center_freq, args.samp_rate, args.lora_bw, args.sf

    if args.region or args.preset:
        if not (args.region and args.preset):
            raise SystemExit("--region and --preset must be given together")
        result = calc_freq(args.region, args.preset, frequency_slot=0, channel_name=args.channel_name)
        if not result["valid"]:
            raise SystemExit(f"[MESHRX] {result['error']}")
        center_freq = center_freq if center_freq is not None else result["center_freq_hz"]
        lora_bw = lora_bw if lora_bw is not None else int(result["bw_khz"] * 1000)
        sf = sf if sf is not None else result["sf"]
        print(f"[MESHRX] {args.region}/{args.preset} -> center_freq={center_freq} bw={lora_bw} sf={sf} "
              f"(slot {result['slot_used']}/{result['num_slots']}, channel={result['channel_name']})", flush=True)
    elif center_freq is None:
        config = load_config()
        if config is None:
            print("[MESHRX] No saved config and no radio parameters given — running first-time setup.\n", flush=True)
            config = run_wizard()
        center_freq = config["center_freq_hz"]
        lora_bw = lora_bw if lora_bw is not None else config["lora_bw_hz"]
        sf = sf if sf is not None else config["sf"]
        samp_rate = samp_rate if samp_rate is not None else config["samp_rate"]
        print(f"[MESHRX] Using saved config ({CONFIG_PATH}): "
              f"{config['region']}/{config['preset']} channel={config['channel_name']}", flush=True)

    # Fill in anything still unset with the historical defaults.
    center_freq = center_freq if center_freq is not None else 869_525_000
    lora_bw = lora_bw if lora_bw is not None else 250_000
    sf = sf if sf is not None else 9
    samp_rate = samp_rate if samp_rate is not None else 1_000_000

    q = queue.Queue(maxsize=4000)

    extra_demod_configs = None
    if args.extra_demod_configs:
        try:
            import json as _json
            extra_demod_configs = _json.loads(args.extra_demod_configs)
        except Exception as e:
            print(f"[MESHRX] Failed to parse extra-demod-configs: {e}", flush=True)

    tb = build_top_block(
        center_freq=center_freq,
        samp_rate=samp_rate,
        lora_bw=lora_bw,
        sf=sf,
        gain=args.gain,
        ppm=args.ppm,
        if_gain=args.if_gain,
        bb_gain=args.bb_gain,
        device_args=args.device_args,
        bias_tee=args.bias_tee,
        extra_demod_configs=extra_demod_configs,
    )

    if args.payload_wait_ms is not None:
        try:
            tb.aggregator.payload_wait_ms = int(args.payload_wait_ms)
        except Exception:
            pass
    if args.metrics_ttl_ms is not None:
        try:
            tb.aggregator.metrics_ttl_ms = int(args.metrics_ttl_ms)
        except Exception:
            pass
    try:
        tb.aggregator.preset_id = int(args.preset_id)
    except Exception:
        pass

    sink = PDUZMQSink(args.bind_host, args.port, q)
    tb.msg_connect(tb.aggregator, "out", sink, "in")
    for chain in getattr(tb, "_extra_chains", []):
        try:
            tb.msg_connect(chain["aggregator"], "out", sink, "in")
        except Exception as e:
            print(f"[MESHRX] Failed to connect extra chain: {e}", flush=True)

    stop = {"flag": False}

    def _sig(_signo, _frame):
        stop["flag"] = True

    signal.signal(signal.SIGINT, _sig)
    signal.signal(signal.SIGTERM, _sig)

    print(f"[MESHRX] ZMQ PUB bound on tcp://{args.bind_host}:{args.port}", flush=True)
    print(f"[MESHRX] center_freq={center_freq} sf={sf} bw={lora_bw} samp_rate={samp_rate}", flush=True)

    tb.start()
    try:
        while not stop["flag"]:
            time.sleep(0.2)
    finally:
        try:
            tb.stop()
            tb.wait()
        except Exception:
            pass
        sink.stop()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
