import sounddevice as sd
import soundfile as sf

TARGET_DEVICE_NAME = "wireless microphone"

CHANNELS = 2
BLOCK_SIZE = 1024
RECORD_SECONDS = 10
OUTPUT_FILE = "recording_anker.wav"

SUPPORTED_RATES = [
    48000,
    44100,
    32000,
    24000,
    16000,
    8000,
]


def select_audio_device():
    for i, dev in enumerate(sd.query_devices()):
        if (
            TARGET_DEVICE_NAME.lower() in dev["name"].lower()
            and dev["max_input_channels"] > 0
        ):
            return i

    return None


def find_supported_samplerate(device_id):
    print("\nTesting sample rates...")

    for rate in SUPPORTED_RATES:
        try:
            sd.check_input_settings(
                device=device_id,
                channels=CHANNELS,
                samplerate=rate,
                dtype="float32",
            )

            print(f"  OK: {rate} Hz")
            return rate

        except Exception as e:
            print(f"  NO: {rate} Hz")

    return None


def main():
    device_id = select_audio_device()

    if device_id is None:
        print(f'Device containing "{TARGET_DEVICE_NAME}" was not found.')
        print("\nAvailable input devices:")

        for i, dev in enumerate(sd.query_devices()):
            if dev["max_input_channels"] > 0:
                print(f"[{i}] {dev['name']}")

        return

    device = sd.query_devices(device_id)

    print("\nSelected device:")
    print(f"  ID:       {device_id}")
    print(f"  Name:     {device['name']}")
    print(f"  Channels: {device['max_input_channels']}")
    print(f"  Default sample rate: {device['default_samplerate']} Hz")

    rate = find_supported_samplerate(device_id)

    if rate is None:
        print("\nERROR: No supported sample rate found.")
        return

    print(f"\nUsing sample rate: {rate} Hz")
    print(f"Recording for {RECORD_SECONDS} seconds...")
    print("Speak into the microphone.")

    try:
        audio = sd.rec(
            int(RECORD_SECONDS * rate),
            samplerate=rate,
            channels=CHANNELS,
            dtype="float32",
            device=device_id,
        )

        sd.wait()

        sf.write(
            OUTPUT_FILE,
            audio,
            rate,
            subtype="PCM_16",
        )

        print(f"\nRecording saved to: {OUTPUT_FILE}")

    except Exception as e:
        print(f"\nAudio recording error: {e}")


if __name__ == "__main__":
    main()