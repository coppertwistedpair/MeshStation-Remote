"""Meshtastic region/preset tables and frequency-hash formula.

Copied from MeshStation's own MESHTASTIC_REGIONS / MESHTASTIC_MODEM_PRESETS /
meshtastic_calc_freq() so MeshRX computes the exact same center frequency
the Meshtastic firmware (and MeshStation's internal engine) would use for a
given region + modem preset + channel name. Keep in sync with that file if
Meshtastic ever changes these tables.
"""

import math

MESHTASTIC_REGIONS = {
    "UNSET":        {"freq_start": 902.0,   "freq_end": 928.0,   "dutycycle": 0.0,   "spacing": 0.0, "power_limit": 0,  "wide_lora": False, "description": "Not Set"},
    "US":           {"freq_start": 902.0,   "freq_end": 928.0,   "dutycycle": 100.0, "spacing": 0.0, "power_limit": 30, "wide_lora": False, "description": "United States"},
    "EU_433":       {"freq_start": 433.0,   "freq_end": 434.0,   "dutycycle": 10.0,  "spacing": 0.0, "power_limit": 10, "wide_lora": False, "description": "EU 433MHz"},
    "EU_868":       {"freq_start": 869.4,   "freq_end": 869.65,  "dutycycle": 10.0,  "spacing": 0.0, "power_limit": 27, "wide_lora": False, "description": "EU 868MHz"},
    "CN":           {"freq_start": 470.0,   "freq_end": 510.0,   "dutycycle": 100.0, "spacing": 0.0, "power_limit": 19, "wide_lora": False, "description": "China"},
    "JP":           {"freq_start": 920.5,   "freq_end": 923.5,   "dutycycle": 100.0, "spacing": 0.0, "power_limit": 13, "wide_lora": False, "description": "Japan"},
    "ANZ":          {"freq_start": 915.0,   "freq_end": 928.0,   "dutycycle": 100.0, "spacing": 0.0, "power_limit": 30, "wide_lora": False, "description": "Australia & NZ"},
    "ANZ_433":      {"freq_start": 433.05,  "freq_end": 434.79,  "dutycycle": 100.0, "spacing": 0.0, "power_limit": 14, "wide_lora": False, "description": "Australia & NZ 433 MHz"},
    "RU":           {"freq_start": 868.7,   "freq_end": 869.2,   "dutycycle": 100.0, "spacing": 0.0, "power_limit": 20, "wide_lora": False, "description": "Russia"},
    "KR":           {"freq_start": 920.0,   "freq_end": 923.0,   "dutycycle": 100.0, "spacing": 0.0, "power_limit": 23, "wide_lora": False, "description": "Korea"},
    "TW":           {"freq_start": 920.0,   "freq_end": 925.0,   "dutycycle": 100.0, "spacing": 0.0, "power_limit": 27, "wide_lora": False, "description": "Taiwan"},
    "IN":           {"freq_start": 865.0,   "freq_end": 867.0,   "dutycycle": 100.0, "spacing": 0.0, "power_limit": 30, "wide_lora": False, "description": "India"},
    "NZ_865":       {"freq_start": 864.0,   "freq_end": 868.0,   "dutycycle": 100.0, "spacing": 0.0, "power_limit": 36, "wide_lora": False, "description": "New Zealand 865MHz"},
    "TH":           {"freq_start": 920.0,   "freq_end": 925.0,   "dutycycle": 100.0, "spacing": 0.0, "power_limit": 16, "wide_lora": False, "description": "Thailand"},
    "UA_433":       {"freq_start": 433.0,   "freq_end": 434.7,   "dutycycle": 10.0,  "spacing": 0.0, "power_limit": 10, "wide_lora": False, "description": "Ukraine 433MHz"},
    "UA_868":       {"freq_start": 868.0,   "freq_end": 868.6,   "dutycycle": 1.0,   "spacing": 0.0, "power_limit": 14, "wide_lora": False, "description": "Ukraine 868MHz"},
    "MY_433":       {"freq_start": 433.0,   "freq_end": 435.0,   "dutycycle": 100.0, "spacing": 0.0, "power_limit": 20, "wide_lora": False, "description": "Malaysia 433MHz"},
    "MY_919":       {"freq_start": 919.0,   "freq_end": 924.0,   "dutycycle": 100.0, "spacing": 0.0, "power_limit": 27, "wide_lora": False, "description": "Malaysia 919MHz"},
    "SG_923":       {"freq_start": 917.0,   "freq_end": 925.0,   "dutycycle": 100.0, "spacing": 0.0, "power_limit": 20, "wide_lora": False, "description": "Singapore 923MHz"},
    "PH_433":       {"freq_start": 433.0,   "freq_end": 434.7,   "dutycycle": 100.0, "spacing": 0.0, "power_limit": 10, "wide_lora": False, "description": "Philippines 433MHz"},
    "PH_868":       {"freq_start": 868.0,   "freq_end": 869.4,   "dutycycle": 100.0, "spacing": 0.0, "power_limit": 14, "wide_lora": False, "description": "Philippines 868MHz"},
    "PH_915":       {"freq_start": 915.0,   "freq_end": 918.0,   "dutycycle": 100.0, "spacing": 0.0, "power_limit": 24, "wide_lora": False, "description": "Philippines 915MHz"},
    "KZ_433":       {"freq_start": 433.075, "freq_end": 434.775, "dutycycle": 100.0, "spacing": 0.0, "power_limit": 10, "wide_lora": False, "description": "Kazakhstan 433MHz"},
    "KZ_863":       {"freq_start": 863.0,   "freq_end": 868.0,   "dutycycle": 100.0, "spacing": 0.0, "power_limit": 30, "wide_lora": False, "description": "Kazakhstan 863MHz"},
    "NP_865":       {"freq_start": 865.0,   "freq_end": 868.0,   "dutycycle": 100.0, "spacing": 0.0, "power_limit": 30, "wide_lora": False, "description": "Nepal 865MHz"},
    "BR_902":       {"freq_start": 902.0,   "freq_end": 907.5,   "dutycycle": 100.0, "spacing": 0.0, "power_limit": 30, "wide_lora": False, "description": "Brazil 902MHz"},
    "LORA_24":      {"freq_start": 2400.0,  "freq_end": 2483.5,  "dutycycle": 0.0,   "spacing": 0.0, "power_limit": 10, "wide_lora": True,  "description": "2.4GHz worldwide"},
}

# RTL-SDR (R820T/T2 tuner) covers roughly 24 MHz - 1766 MHz. LORA_24 (2.4GHz)
# is physically out of range on an RTL-SDR, so exclude it from the wizard.
RTLSDR_TUNABLE_REGIONS = {
    k: v for k, v in MESHTASTIC_REGIONS.items()
    if k != "UNSET" and not v.get("wide_lora", False)
}

MESHTASTIC_MODEM_PRESETS = {
    "LONG_FAST":       {"channel_name": "LongFast",    "bw_narrow": 250.0,  "bw_wide": 812.5, "sf": 11, "cr": 5, "description": "Long Range, Fast (default)"},
    "MEDIUM_FAST":     {"channel_name": "MediumFast",  "bw_narrow": 250.0,  "bw_wide": 812.5, "sf": 9,  "cr": 5, "description": "Medium Range, Fast"},
    "LONG_SLOW":       {"channel_name": "LongSlow",    "bw_narrow": 125.0,  "bw_wide": 406.25,"sf": 12, "cr": 8, "description": "Long Range, Slow (deprecated)"},
    "MEDIUM_SLOW":     {"channel_name": "MediumSlow",  "bw_narrow": 250.0,  "bw_wide": 812.5, "sf": 10, "cr": 5, "description": "Medium Range, Slow"},
    "SHORT_FAST":      {"channel_name": "ShortFast",   "bw_narrow": 250.0,  "bw_wide": 812.5, "sf": 7,  "cr": 5, "description": "Short Range, Fast"},
    "SHORT_SLOW":      {"channel_name": "ShortSlow",   "bw_narrow": 250.0,  "bw_wide": 812.5, "sf": 8,  "cr": 5, "description": "Short Range, Slow"},
    "SHORT_TURBO":     {"channel_name": "ShortTurbo",  "bw_narrow": 500.0,  "bw_wide": 1625.0,"sf": 7,  "cr": 5, "description": "Short Range, Turbo (not legal everywhere)"},
    "LONG_TURBO":      {"channel_name": "LongTurbo",   "bw_narrow": 500.0,  "bw_wide": 1625.0,"sf": 11, "cr": 8, "description": "Long Range, Turbo"},
    "LONG_MODERATE":   {"channel_name": "LongMod",     "bw_narrow": 125.0,  "bw_wide": 406.25,"sf": 11, "cr": 8, "description": "Long Range, Moderate"},
    "VERY_LONG_SLOW":  {"channel_name": "VLongSlow",   "bw_narrow": 62.5,   "bw_wide": 250.0, "sf": 12, "cr": 8, "description": "Very Long Range, Very Slow"},
}


def _djb2_hash(s: str) -> int:
    h = 5381
    for c in s:
        h = ((h << 5) + h + ord(c)) & 0xFFFFFFFF
    return h


def calc_freq(region_key: str, preset_key: str, frequency_slot: int = 0, channel_name: str | None = None) -> dict:
    """Calculate center frequency exactly as Meshtastic firmware does.

    Args:
        region_key: e.g. "EU_868", "US"
        preset_key: e.g. "LONG_FAST", "MEDIUM_SLOW"
        frequency_slot: 1-based manual slot (0 = auto/hash-based, matches
            Meshtastic's default per-channel-name frequency hashing)
        channel_name: custom channel name for hash (None = use preset default)

    Returns dict with center_freq_hz, bw_khz, sf, cr, num_slots, slot_used,
    channel_name, valid, error.
    """
    region = MESHTASTIC_REGIONS.get(region_key)
    preset = MESHTASTIC_MODEM_PRESETS.get(preset_key)

    if not region:
        return {"valid": False, "error": f"Unknown region: {region_key}"}
    if not preset:
        return {"valid": False, "error": f"Unknown preset: {preset_key}"}

    wide_lora = region.get("wide_lora", False)
    bw_khz = preset["bw_wide"] if wide_lora else preset["bw_narrow"]
    sf = preset["sf"]
    cr = preset["cr"]
    spacing = region.get("spacing", 0.0)
    freq_start = region["freq_start"]
    freq_end = region["freq_end"]

    bw_mhz = bw_khz / 1000.0

    # num_channels = floor((freqEnd - freqStart) / (spacing + bw_MHz))
    band_width = freq_end - freq_start
    slot_width = spacing + bw_mhz
    if slot_width <= 0:
        return {"valid": False, "error": "Invalid slot width (spacing + bw <= 0)"}

    num_slots = int(math.floor(band_width / slot_width))
    if num_slots < 1:
        return {"valid": False, "error": f"Band too narrow for preset: only {band_width:.3f}MHz available, need {slot_width:.3f}MHz per slot."}

    ch_name = channel_name if channel_name else preset["channel_name"]
    if frequency_slot != 0:
        channel_num_0 = (frequency_slot - 1) % num_slots
    else:
        channel_num_0 = _djb2_hash(ch_name) % num_slots

    # freq = freqStart + spacing/2 + channel_num * (spacing + bw_MHz)
    freq_mhz = freq_start + (bw_mhz / 2.0) + channel_num_0 * slot_width

    return {
        "valid": True,
        "error": None,
        "center_freq_mhz": freq_mhz,
        "center_freq_hz": int(round(freq_mhz * 1_000_000)),
        "num_slots": num_slots,
        "slot_used": channel_num_0 + 1,
        "bw_khz": bw_khz,
        "sf": sf,
        "cr": cr,
        "channel_name": ch_name,
    }
