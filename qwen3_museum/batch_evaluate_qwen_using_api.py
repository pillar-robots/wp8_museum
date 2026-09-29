import argparse
import collections
import json
import os
import statistics
import time
from pathlib import Path

import requests
from PIL import Image, UnidentifiedImageError


STANDARD_KEYS = [
    "Age composition",
    "Spatial formation",
    "Interpersonal spacing",
    "Postural assessment",
    "Area positioning",
    "Engagement rating",
]

DEFAULT_FOLDER = "demo_phots_for_evaluation"
DEFAULT_TRUTH = "evaluation_ground_truth.json"
DEFAULT_URL = "http://127.0.0.1:5555/api/relations"
DEFAULT_MODEL = "qwen3.5:9b"
REPO_ROOT = Path(__file__).resolve().parent


def _round_area(value):
    try:
        return round(float(value), 1)
    except (TypeError, ValueError):
        return None


def is_valid_image(path):
    try:
        with Image.open(path) as img:
            img.verify()
        return True, ""
    except (OSError, UnidentifiedImageError) as exc:
        return False, str(exc)


def load_truth(truth_path):
    truth_file = Path(truth_path)
    if not truth_file.is_absolute():
        truth_file = REPO_ROOT / truth_file
    return json.loads(truth_file.read_text())


def process_single_image(image_path, url=DEFAULT_URL, timeout=300, model=DEFAULT_MODEL):
    if not os.path.exists(image_path):
        print(f"Error: File '{image_path}' not found.")
        return None

    data = {
        "message": {
            "text": "Describe the interaction with the guide",
            "files": [image_path],
            "model": model,
        }
    }

    start_time = time.time()
    try:
        res = requests.post(url, json=data, timeout=timeout)
    except requests.exceptions.RequestException as exc:
        print(f"Error connecting to API: {exc}")
        return None

    inference_latency = time.time() - start_time
    if res.status_code != 200:
        print(f"API Error {res.status_code}: {res.text}")
        return None

    raw_data = res.json()
    if isinstance(raw_data, str):
        try:
            clean_str = raw_data.replace("```json", "").replace("```", "").strip()
            raw_data = json.loads(clean_str)
        except json.JSONDecodeError:
            raw_data = {}

    if "results" in raw_data and isinstance(raw_data["results"], list):
        processed_entry = {}
        for part in raw_data["results"]:
            if isinstance(part, dict):
                processed_entry.update(part)
    else:
        processed_entry = raw_data

    final_json = {key: processed_entry.get(key, "Not Observed") for key in STANDARD_KEYS}
    final_json["inference_time_seconds"] = round(inference_latency, 2)
    return final_json


def is_correct(predicted, expected):
    return str(predicted).strip().lower() == str(expected).strip().lower()


def is_correct_field(field, predicted, expected):
    if field == "Area positioning":
        pred_score = _round_area(predicted)
        exp_score = _round_area(expected)
        return pred_score is not None and exp_score is not None and pred_score == exp_score
    return is_correct(predicted, expected)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", default=str(REPO_ROOT / DEFAULT_FOLDER))
    parser.add_argument("--truth", default=DEFAULT_TRUTH)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    return parser.parse_args()


def run_batch_evaluation(folder_path, truth_path, url, iterations=10, model=DEFAULT_MODEL):
    folder_path = Path(folder_path)
    truth = load_truth(truth_path)
    image_files = sorted(truth.keys())

    print(f"\nStarting batch evaluation on folder: {folder_path}")

    overall_correct = 0
    overall_total = 0

    for filename in image_files:
        image_path = folder_path / filename
        gt = truth.get(filename)
        print(f"\nProcessing '{filename}' ({iterations} runs)...")

        valid, reason = is_valid_image(image_path)
        if not valid:
            print(f"SKIPPED: invalid image file ({reason})")
            continue

        stats_tally = {key: collections.Counter() for key in STANDARD_KEYS}
        successful_runs = 0
        inference_times = []

        for i in range(iterations):
            print(f"  -> Run {i + 1}/{iterations}...", end=" ", flush=True)
            result = process_single_image(str(image_path), url=url, model=model)
            if not result:
                print("Failed.")
                continue

            successful_runs += 1
            inference_times.append(result["inference_time_seconds"])
            for key in STANDARD_KEYS:
                stats_tally[key][result.get(key, "Not Observed")] += 1
            print(f"Done ({result['inference_time_seconds']}s)")

            if gt is not None:
                run_correct = 0
                for key in STANDARD_KEYS:
                    pred = result.get(key, "Not Observed")
                    exp = gt.get(key, "N/A")
                    ok = is_correct_field(key, pred, exp)
                    run_correct += int(ok)
                    mark = "✓" if ok else "✗"
                    if key == "Area positioning":
                        pred_score = _round_area(pred)
                        exp_score = _round_area(exp)
                        pred_display = f"{pred_score:.1f}" if pred_score is not None else str(pred)
                        exp_display = f"{exp_score:.1f}" if exp_score is not None else str(exp)
                        extra = "" if ok else f"   (GT: {exp_display})"
                        print(f"       {mark} {key:22s}: {pred_display}{extra}")
                    else:
                        extra = "" if ok else f"   (GT: {exp})"
                        print(f"       {mark} {key:22s}: {pred}{extra}")
                overall_correct += run_correct
                overall_total += len(STANDARD_KEYS)
                print(f"       => {run_correct}/{len(STANDARD_KEYS)} correct")

        if successful_runs > 0:
            avg_time = statistics.mean(inference_times)
            print(f"  IMAGE SCORE: {sum(1 for k in STANDARD_KEYS if is_correct_field(k, stats_tally[k].most_common(1)[0][0], gt.get(k, 'N/A')))}/{len(STANDARD_KEYS)} keys correct" if gt else f"  IMAGE DONE: {successful_runs} successful runs")

    print("\n" + "=" * 50)
    if overall_total:
        print(
            f"OVERALL ACCURACY: {overall_correct}/{overall_total} "
            f"({overall_correct / overall_total * 100:.1f}%) across all runs with ground truth"
        )
    print("=" * 50)


def main():
    args = parse_args()
    run_batch_evaluation(args.folder, args.truth, args.url, iterations=args.iterations, model=args.model)


if __name__ == "__main__":
    main()
