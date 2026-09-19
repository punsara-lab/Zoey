"""
ZOEY — list_audio_devices.py
Prints every audio device sounddevice can see, with its index, so you
can fix mic driver issues. On Windows, the MME driver commonly throws
PortAudioError -9999 — the WASAPI or WDM-KS version of the same physical
mic is usually more reliable. Once you find a working index, hardcode it
in config.py as MIC_DEVICE_INDEX.
"""

import sounddevice as sd

if __name__ == "__main__":
    print(sd.query_devices())
    try:
        default_input = sd.default.device[0]
        print(f"\nDefault input device: {default_input}")
    except Exception:
        pass
