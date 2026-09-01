"""First-time setup wizard: picks the correct Meshtastic region + modem
preset and derives the matching RTL-SDR radio parameters, instead of making
the user guess a center frequency by hand.
"""

import json
import os

from .meshtastic_presets import (
    MESHTASTIC_MODEM_PRESETS,
    RTLSDR_TUNABLE_REGIONS,
    calc_freq,
)

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "meshrx_config.json")


def _samp_rate_for_bw(bw_khz: float) -> int:
    # Need roughly >= 4x the LoRa bandwidth for the demod chain's decimating
    # filter; keep the historical 1 Msps floor and cap at what an RTL-SDR
    # (R820T/T2) can sustain reliably.
    return max(1_000_000, min(3_200_000, int(bw_khz * 1000 * 4)))


def _prompt_choice(title: str, options: dict) -> str:
    keys = list(options.keys())
    print(f"\n{title}")
    for i, k in enumerate(keys, 1):
        desc = options[k].get("description", "")
        print(f"  {i:2d}) {k:<14} {desc}")
    while True:
        raw = input(f"Select 1-{len(keys)}: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(keys):
            return keys[int(raw) - 1]
        print("Invalid choice, try again.")


def run_wizard(save: bool = True) -> dict:
    print("=== MeshRX first-time setup ===")
    print("Pick the Meshtastic region and modem preset your mesh uses.")
    print("This computes the exact center frequency Meshtastic firmware")
    print("would use for that region/preset/channel-name combination.\n")

    region_key = _prompt_choice("Region:", RTLSDR_TUNABLE_REGIONS)
    preset_key = _prompt_choice("Modem preset:", MESHTASTIC_MODEM_PRESETS)

    default_name = MESHTASTIC_MODEM_PRESETS[preset_key]["channel_name"]
    channel_name = input(f"\nChannel name [{default_name}]: ").strip() or default_name

    result = calc_freq(region_key, preset_key, frequency_slot=0, channel_name=channel_name)
    if not result["valid"]:
        raise SystemExit(f"Setup error: {result['error']}")

    samp_rate = _samp_rate_for_bw(result["bw_khz"])

    config = {
        "region": region_key,
        "preset": preset_key,
        "channel_name": result["channel_name"],
        "center_freq_hz": result["center_freq_hz"],
        "lora_bw_hz": int(result["bw_khz"] * 1000),
        "sf": result["sf"],
        "samp_rate": samp_rate,
        "slot_used": result["slot_used"],
        "num_slots": result["num_slots"],
    }

    print("\n--- Computed radio parameters ---")
    print(f"  Region:          {region_key}")
    print(f"  Preset:          {preset_key} ({MESHTASTIC_MODEM_PRESETS[preset_key]['description']})")
    print(f"  Channel name:    {config['channel_name']}")
    print(f"  Center freq:     {result['center_freq_mhz']:.4f} MHz (slot {config['slot_used']}/{config['num_slots']})")
    print(f"  LoRa bandwidth:  {config['lora_bw_hz']} Hz")
    print(f"  Spreading factor:{config['sf']}")
    print(f"  Sample rate:     {config['samp_rate']} sps")

    if save:
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
        print(f"\nSaved to {CONFIG_PATH}")
        print("Run meshrx.py again to start receiving with these settings,")
        print("or pass --setup any time to redo this wizard.")

    return config


def load_config() -> dict | None:
    if not os.path.isfile(CONFIG_PATH):
        return None
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except Exception:
        return None


if __name__ == "__main__":
    run_wizard()
