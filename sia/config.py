"""SIA Mission Intercept — central configuration and constants."""

# FRS/GMRS channel -> centre frequency in MHz
FRS_CHANNELS = {
    1:  462.5625,
    2:  462.5875,
    3:  462.6125,
    4:  462.6375,
    5:  462.6625,
    6:  462.6875,
    7:  462.7125,
    8:  467.5625,
    9:  467.5875,
    10: 467.6125,
    11: 467.6375,
    12: 467.6625,
    13: 467.6875,
    14: 467.7125,
    15: 462.5500,
    16: 462.5750,
    17: 462.6000,
    18: 462.6250,
    19: 462.6500,
    20: 462.6750,
    21: 462.7000,
    22: 462.7250,
}

# Reverse lookup: frequency (rounded) -> channel number
FREQ_TO_CHANNEL = {round(freq, 4): ch for ch, freq in FRS_CHANNELS.items()}

DEFAULT_FREQ    = 462.6125   # FRS Channel 3
DEFAULT_GAIN    = 20
DEFAULT_SQUELCH = 70
DEFAULT_AGENT   = "MegaSpy"
DEFAULT_OUTPUT  = "./recordings"
DEFAULT_VOLUME  = 10.0       # software audio gain (1000%) — start maxed; FRS NBFM audio is faint

SAMPLE_RATE = 48000
CHUNK_SIZE  = 4096

# rtl_fm capture sample rate (the '-s' flag) before resampling to SAMPLE_RATE
CAPTURE_RATE = "200k"

APP_NAME    = "Mission Intercept"
APP_VERSION = "1.0.0"
ORG_NAME    = "Spy Intelligence Agency"
ORG_ABBR    = "SIA"
AGENTS      = "MegaSpy & Spyhunter"

# Valid operator ranges
GAIN_MIN, GAIN_MAX = 0, 50
VOLUME_MIN, VOLUME_MAX = 0.0, 20.0
VOLUME_STEP = 1.0

# Signal detection: mean absolute sample value above this counts as "signal"
SIGNAL_THRESHOLD = 200

# Recording filename prefix
RECORDING_PREFIX = "SIA_INTERCEPT"


def channel_for_freq(freq):
    """Return the FRS channel number for a frequency in MHz, or None."""
    return FREQ_TO_CHANNEL.get(round(float(freq), 4))


def freq_for_channel(channel):
    """Return the centre frequency in MHz for an FRS channel, or None."""
    return FRS_CHANNELS.get(int(channel))
