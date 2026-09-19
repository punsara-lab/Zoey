import time
import numpy as np
import sounddevice as sd

def test_device(device_index=None, duration=5):
    """Listens to a specific input device for `duration` seconds and prints a live audio level meter."""
    try:
        if device_index is None:
            info = sd.query_devices(kind="input")
            device_name = f"Default Input ({info['name']})"
        else:
            info = sd.query_devices(device_index, "input")
            device_name = info["name"]
    except Exception as e:
        print(f"❌ Could not query device {device_index}: {e}")
        return

    print(f"\n==================================================")
    print(f" Testing Device [{device_index if device_index is not None else 'DEFAULT'}]: {device_name}")
    print(f" Host API: {sd.query_hostapis(info['hostapi'])['name']}")
    print(f" Speak or clap into your mic now! (Testing for {duration} seconds)")
    print(f"==================================================")

    max_peak = 0.0

    def audio_callback(indata, frames, time_info, status):
        nonlocal max_peak
        if status:
            print(f"\n[Warning] {status}")
        
        peak = float(np.max(np.abs(indata))) if len(indata) > 0 else 0.0
        if peak > max_peak:
            max_peak = peak

        # Visual bar chart (normalized 0.0 to 1.0)
        bar_len = 30
        filled = int(min(1.0, peak * 2) * bar_len)  # Boost visual gain slightly for visibility
        meter = "█" * filled + "░" * (bar_len - filled)
        pct = int(peak * 100)
        print(f"\rLevel: [{meter}] {pct:3d}% (Peak: {int(max_peak * 100)}%)", end="", flush=True)

    try:
        # Standard 44100Hz 1-channel mono stream test
        with sd.InputStream(
            device=device_index,
            channels=1,
            samplerate=44100,
            dtype="float32",
            callback=audio_callback,
        ):
            time.sleep(duration)
        
        print("\n")
        if max_peak < 0.02:
            print("❌ RESULT: NEAR TOTAL SILENCE (Peak < 2%)")
            print("   This device received no active audio signal.")
        else:
            print(f"✅ SUCCESS! Working mic detected. Peak level reached {int(max_peak * 100)}%.")

    except Exception as e:
        print(f"\n❌ FAILED to open stream: {e}")


if __name__ == "__main__":
    print("--- ZOEY MICROPHONE DIAGNOSTIC TOOL ---")
    
    # 1. Test Default Input Device
    test_device(device_index=None, duration=4)

    # 2. Test specific candidate devices based on your device list
    candidate_indices = [1, 8, 17, 20]
    
    print("\n--------------------------------------------------")
    print("Testing candidate indices (1, 8, 17, 20)...")
    print("--------------------------------------------------")
    
    for idx in candidate_indices:
        test_device(device_index=idx, duration=4)