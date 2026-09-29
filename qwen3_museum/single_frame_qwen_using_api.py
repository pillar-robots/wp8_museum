import argparse
import json
from pathlib import Path

import requests


DEFAULT_IMAGE = "/home/citic_lab/Pictures/Webcam/2026-06-25-153254.jpg"
DEFAULT_URL = "http://127.0.0.1:5555/api/relations"
DEFAULT_MODEL = "qwen3.5:9b"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    return parser.parse_args()


def main():
    args = parse_args()
    image_path = Path(args.image)
    if not image_path.exists():
        raise SystemExit(f"Image not found: {image_path}")

    payload = {
        "message": {
            "text": "Describe the interaction with the guide",
            "files": [str(image_path)],
            "model": args.model,
        }
    }
    response = requests.post(args.url, json=payload, timeout=120)
    response.raise_for_status()

    print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    main()
