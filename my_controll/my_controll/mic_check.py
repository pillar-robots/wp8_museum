import sounddevice as sd

TARGET_KEYWORDS = [
    "shure",
    "aniusb",
    "matrix",
    "pulse"
]

def find_mic_index():
    devices = sd.query_devices()

    print("📋 Dostupné vstupní audio zařízení:\n")
 
    for idx, device in enumerate(devices):
        if device["max_input_channels"] > 0:
            name_lower = device["name"].lower()

            print(f"ID {idx}: {device['name']}")

            # hledání podle klíčových slov (USB, Shure, ANIUSB)
            if any(keyword in name_lower for keyword in TARGET_KEYWORDS):
                print(f"✅ NALEZENO – použij:")
                print(f"MIC_INDEX = {idx}  # {device['name']}")
                return idx

    print("\n❌ Shure USB mikrofon nebyl nalezen.")
    return None


if __name__ == "__main__":
    mic_index = find_mic_index()

    if mic_index is not None:
        print("\n➡️ Hotovo. MIC_INDEX můžeš rovnou použít v hlavním kódu.")
 