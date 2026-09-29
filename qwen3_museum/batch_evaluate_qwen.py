import os
import json
import time
import collections
import statistics
import io
from pathlib import Path
import matplotlib.pyplot as plt
from PIL import Image
from ollama import Client

# --- 0. Ollama (Qwen) Config ---
client = Client(host="http://127.0.0.1:11434")
MODEL_NAME = "qwen3.5:27b"
# MODEL_NAME = "qwen3.5:35b"
# MODEL_NAME = "qwen3-vl:32b"

USER_TEXT = "Describe the interaction with the guide"

# --- Ground truth + correctness ---
GROUND_TRUTH_PATH = Path(__file__).resolve().with_name("evaluation_ground_truth.json")
try:
    with GROUND_TRUTH_PATH.open() as f:
        GROUND_TRUTH = json.load(f)
except Exception as e:
    print(f"[!] Could not load ground truth ({e}). Correctness will be skipped.")
    GROUND_TRUTH = {}

# Map differing wordings (GT vs model output) to a common canonical form so
# "Separate" == "Separated" and "Sitting Only" == "Primarily Seated" still match.
_SYNONYMS = {
    "separate": "separated",
    "separated": "separated",
    "sitting only": "seated",
    "seated only": "seated",
    "primarily seated": "seated",
    "standing only": "standing",
}

def _norm(value):
    s = str(value).strip().lower()
    return _SYNONYMS.get(s, s)

def is_correct(predicted, expected):
    return _norm(predicted) == _norm(expected)

def _round_area(value):
    try:
        return round(float(value), 1)
    except (TypeError, ValueError):
        return None

def is_correct_field(field, predicted, expected):
    if field == "Area positioning":
        pred_score = _round_area(predicted)
        exp_score = _round_area(expected)
        return pred_score is not None and exp_score is not None and pred_score == exp_score
    return is_correct(predicted, expected)

SYSTEM_PROMPT = """You are a highly constrained vision-language image analysis model (LVLM) specialized in group interaction analysis.

***PRIMARY INSTRUCTION:***
Your SOLE job is to analyze the provided image and extract the six required analysis elements below, strictly adhering to the "ANALYSIS RULES" and the "OUTPUT FORMAT (STRICT)".

ANALYSIS ELEMENTS TO EXTRACT:
1. Age composition
2. Spatial formation
3. Interpersonal spacing
4. Postural assessment
5. Area positioning
6. Engagement rating

ANALYSIS RULES:

RULE 1: AGE COMPOSITION
- Determine the predominant age composition of the group.
Classification Terms:
Mixed Adults: (Significant mix of young, middle-aged or senior adults).
Mixed People: (Significant mix of adolescents and adults).
Kids: (Majority appear 2-10 years old).
Adolescents: (Majority appear 10-18 years old).
Primarily Young Adults: (Majority appear 18-35 years old).
Primarily Middle-Aged: (Majority appear 35-65 years old).
Seniors/Older Adults: (Majority appear 65+ years old).

RULE 2: SPATIAL FORMATION
- Determine if the individuals are arranged in a linear formation.
- CRITICAL OVERRIDE: Look at the overall axis formed by their shoes (if standing) or hips (if seated). Do not penalize for minor natural variations (e.g., one person's foot slightly forward). Perspective angles might make a straight line look diagonal—this is still a row. 
Classification Terms:
In a Row: People are aligned generally side-by-side or front-to-back along a single straight axis.
Not in a Row: The group forms a deliberate, distinct curve, arc, half-circle, or is clearly scattered, clustered, or deeply staggered in depth.

RULE 3: INTERPERSONAL SPACING
- Determine the physical proximity between the individuals.
- CRITICAL OVERRIDE: If the contour of one person's upper arm or shoulder visually touches, overlaps, or is close (within hand reaching range) to the next person's, they are "Close". Ignore visual gaps between their legs. If people are on a line shoulder to shoulder, they are "Close".
Classification Terms:
Close: Individuals are huddled, shoulder-to-shoulder, sitting side-by-side, or within immediate touching distance.
Separated: There is a distinct, wide, explicit visual gap between the individuals' upper bodies (e.g., at least a full arm's length or shoulder-width apart).

RULE 4: POSTURAL ASSESSMENT
- Determine the dominant physical state of the group.
Classification Terms:
Standing Only: All visible people are standing upright.
Mixed (Standing/Seated): A clear mix of standing and sitting.
Primarily Seated: All visible people are sitting.

RULE 5: AREA POSITIONING
- The marked area on the floor is bounded by a yellow-and-black striped line (or parallel lines forming a square/rectangular zone).
- CRITICAL OVERRIDE: Ignore the upper bodies. 
- If STANDING: Look ONLY at the exact spot where their shoes touch the floor.
- If SEATED: completely IGNORE their extended legs/feet. Look strictly at the base of their torso/hips.
- COUNTING PROTOCOL: You must explicitly count the total number of people, count how many have their contact points inside/on the line, and calculate the exact percentage of people inside.
Classification Terms:
Instead of a word, output the calculated percentage as a string (e.g., "0", "0.14", "0.50", "0.75", "1.00"). 

RULE 6: ENGAGEMENT RATING
- Evaluate the collective visual focus of the group specifically towards the CAMERA lens.
- CRITICAL OVERRIDE: Do not guess based only on visible faces. You must evaluate eyes/faces, head/body orientation, and whether the group looks collectively posed/attentive or only casually present.
- High Engagement is rare. Use it only when almost everyone is clearly looking at the camera AND the group is cohesive/posed.
- Standing Only can be High Engagement ONLY when the people form a deliberate row/line facing the camera and almost all faces are attentive; small natural gaps in the row do not prevent High Engagement. If the standing group is loose, staggered, scattered, or Not in a Row, High Engagement is forbidden. Choose Moderate when several people in the main standing group face the camera/guide and no peer-facing cluster dominates. Choose Low when several people are turned toward peers, sideways, or with backs partly to the camera.
- Seated Only can be High Engagement when the seated group has clear shared attention toward the camera.
- Clear Mixed (Standing/Seated) scenes with main-group participants actually seated on the floor/chairs should be Low Engagement. Do not output Moderate or High for these clear mixed seated/standing groups. Do not apply this to a standing group just because of a distant, background, or ambiguous person.
Classification Terms:
High Engagement: ALMOST EVERYONE (roughly 80% to 100%) is making direct eye contact with the camera AND the group is either a deliberate standing row/line facing the camera or a seated-only attentive group.
Moderate Engagement: Several or most people look toward the camera/guide, but the group is loose, separated, standing casually, or not clearly posed; use this for Standing Only + Separate/Not in a Row scenes when several main participants still face the camera/guide.
Low Engagement: Most people are not collectively engaged: backs turned, looking at the floor, looking sideways at peers, passive seated posture, clear mixed standing/seated floor-sitting group, peer-facing social cluster, or only one/two people clearly attending.

OUTPUT FORMAT (STRICT):
**Return ONLY a raw JSON object. Do not include markdown code blocks, preamble, or postscript. If a rule cannot be assessed, use "Not Observed"**
**YOU MUST USE THE EXACT KEY NAMES PROVIDED.**
REQUIRED SCHEMA:
{
"Spatial_analysis_reasoning": "Step 1: Locate the marked area (look for yellow-and-black stripes or parallel lines). Step 2: Are the people standing or sitting? Step 3: Identify their contact points (shoes if standing, hips if sitting). Step 4: Do these contact points sit on the boundary lines or inside the area, or are they entirely outside? Step 5: Group shape - look at the line connecting their shoes/hips. Is it perfectly straight or an arc/semicircle? Step 6: Shoulders - trace the upper arms. Do they touch/overlap or have a wide gap?",
"Age composition": "Select from Rule 1",
"Spatial formation": "Select from Rule 2",
"Interpersonal spacing": "Select from Rule 3",
"Postural assessment": "Select from Rule 4",
"Area positioning": "Select from Rule 5 strictly based on Step 4",
"Engagement rating": "Select from Rule 6"
}"""


# --- 1. The Processing Function (local Qwen via Ollama instead of Gemini) ---
def process_single_image(image_path, model_name=None, num_predict=1000):
    if not os.path.exists(image_path):
        print(f"Error: File '{image_path}' not found.")
        return None

    standard_keys = [
        "Age composition", "Spatial formation", "Interpersonal spacing",
        "Postural assessment", "Area positioning", "Engagement rating"
    ]

    start_time = time.time()
    try:
        response = client.chat(
            model=model_name or MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_TEXT, "images": [image_path]},
                {"role": "assistant", "content": "{"},
            ],
            options={
                "keep_alive": -1,
                "num_predict": num_predict,
                "temperature": 0.1,
                "top_k": 50,
                "top_p": 0.5,
            },
        )
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        return None

    inference_latency = time.time() - start_time

    raw_data = response["message"]["content"] if "message" in response else ""
    # The assistant turn was primed with "{", so re-attach it if the model
    # continued without repeating it.
    clean_str = raw_data.replace("```json", "").replace("```", "").strip()
    if not clean_str.startswith("{"):
        clean_str = "{" + clean_str
    try:
        parsed = json.loads(clean_str)
    except json.JSONDecodeError:
        print(f"  [!] Could not parse JSON: {raw_data[:200]}")
        parsed = {}

    final_json = {key: parsed.get(key, "Not Observed") for key in standard_keys}
    final_json["inference_time_seconds"] = round(inference_latency, 2)
    return final_json


# --- 2. Matplotlib Image Report Generation ---
def generate_report_image(original_image_path, stats_tally, time_stats, successful_runs, iterations, output_path):
    standard_keys = [
        "Age composition", "Spatial formation", "Interpersonal spacing",
        "Postural assessment", "Area positioning", "Engagement rating"
    ]

    fig, axes = plt.subplots(3, 2, figsize=(14, 10), constrained_layout=True)
    fig.patch.set_facecolor('white')

    title_text = (
        f"QWEN CONSISTENCY REPORT ({successful_runs}/{iterations} SUCCESSFUL)\n"
        f"Latency - Avg: {time_stats['avg']:.2f}s | Min: {time_stats['min']:.2f}s | Max: {time_stats['max']:.2f}s | Std Dev: {time_stats['std']:.2f}s"
    )
    fig.suptitle(title_text, fontsize=16, fontweight='bold', color='#333333')

    axes = axes.flatten()

    for idx, key in enumerate(standard_keys):
        ax = axes[idx]
        tally = stats_tally[key]

        labels = [item[0] for item in tally.most_common()]
        counts = [item[1] for item in tally.most_common()]

        if not labels:
            labels, counts = ["No Data"], [0]

        labels = labels[::-1]
        counts = counts[::-1]

        bars = ax.barh(labels, counts, color='#4A90E2', edgecolor='#2A5282', height=0.3)

        ax.set_title(key.upper(), fontsize=12, fontweight='bold', color='#444444', pad=10)
        ax.set_xlim(0, iterations)

        ax.xaxis.grid(True, linestyle='--', alpha=0.7)
        ax.set_axisbelow(True)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        for bar, count in zip(bars, counts):
            percentage = (count / successful_runs * 100) if successful_runs > 0 else 0
            ax.text(bar.get_width() + (iterations * 0.02), bar.get_y() + bar.get_height()/2,
                    f'{count} ({percentage:.0f}%)',
                    va='center', ha='left', fontsize=11, fontweight='bold', color='#333333')

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close(fig)
    chart_img = Image.open(buf)

    try:
        orig_img = Image.open(original_image_path).convert("RGB")
    except Exception as e:
        print(f"Could not open original image: {e}")
        chart_img.save(output_path)
        return

    aspect_ratio = orig_img.height / orig_img.width
    new_orig_width = chart_img.width
    new_orig_height = int(new_orig_width * aspect_ratio)
    orig_img_resized = orig_img.resize((new_orig_width, new_orig_height), Image.Resampling.LANCZOS)

    composite = Image.new("RGB", (chart_img.width, new_orig_height + chart_img.height), "white")
    composite.paste(orig_img_resized, (0, 0))
    composite.paste(chart_img, (0, new_orig_height))

    composite.save(output_path)


# --- 3. The Batch Processing Function ---
def run_batch_evaluation(folder_path, iterations=10):
    if not os.path.exists(folder_path):
        print(f"Folder not found: {folder_path}")
        return

    print(f"\nStarting batch evaluation on folder: {folder_path}")

    output_visual_dir = os.path.join(folder_path, "evaluation_visual_reports_qwen")
    os.makedirs(output_visual_dir, exist_ok=True)

    valid_extensions = ('.png', '.jpg', '.jpeg')
    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(valid_extensions)]

    if not image_files:
        print("No images found in the specified folder.")
        return

    master_report = {
        "folder_evaluated": folder_path,
        "model": MODEL_NAME,
        "iterations_per_image": iterations,
        "images_data": {}
    }

    standard_keys = [
        "Age composition", "Spatial formation", "Interpersonal spacing",
        "Postural assessment", "Area positioning", "Engagement rating"
    ]

    # Global accuracy accumulators (across all images, only where GT exists)
    overall_correct = 0
    overall_total = 0

    for filename in image_files:
        image_path = os.path.join(folder_path, filename)
        gt = GROUND_TRUTH.get(filename)
        print(f"\nProcessing '{filename}' ({iterations} runs)...")
        if gt is None:
            print("  (no ground truth for this image — correctness skipped)")

        stats_tally = {key: collections.Counter() for key in standard_keys}
        inference_times = []
        successful_runs = 0
        all_raw_results = []

        for i in range(iterations):
            print(f"  -> Run {i + 1}/{iterations}...", end=" ", flush=True)
            result = process_single_image(image_path)

            if result:
                successful_runs += 1
                inference_times.append(result["inference_time_seconds"])
                all_raw_results.append(result)

                for key in standard_keys:
                    answer = result.get(key, "Not Observed")
                    stats_tally[key][answer] += 1

                print(f"Done ({result['inference_time_seconds']}s)")

                # Print correctness for this run against ground truth
                if gt is not None:
                    run_correct = 0
                    for key in standard_keys:
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
                    overall_total += len(standard_keys)
                    print(f"       => {run_correct}/{len(standard_keys)} correct")
            else:
                print("Failed.")

        if successful_runs > 0:
            avg_time = statistics.mean(inference_times)
            min_time = min(inference_times)
            max_time = max(inference_times)
            std_time = statistics.stdev(inference_times) if len(inference_times) >= 2 else 0.0

            time_stats = {
                "avg": avg_time,
                "min": min_time,
                "max": max_time,
                "std": std_time
            }

            output_img_name = f"{os.path.splitext(filename)[0]}_stats.png"
            output_img_path = os.path.join(output_visual_dir, output_img_name)
            generate_report_image(image_path, stats_tally, time_stats, successful_runs, iterations, output_img_path)

            image_summary = {}
            for key in standard_keys:
                image_summary[key] = {}
                for answer, count in stats_tally[key].items():
                    percentage = (count / successful_runs) * 100
                    image_summary[key][answer] = f"{count}/{successful_runs} ({percentage:.1f}%)"

            # Correctness on the majority (most common) answer per key
            correctness = None
            if gt is not None:
                correctness = {}
                img_correct = 0
                for key in standard_keys:
                    majority = stats_tally[key].most_common(1)[0][0]
                    exp = gt.get(key, "N/A")
                    ok = is_correct_field(key, majority, exp)
                    img_correct += int(ok)
                    if key == "Area positioning":
                        majority_score = _round_area(majority)
                        exp_score = _round_area(exp)
                        majority_display = f"{majority_score:.1f}" if majority_score is not None else majority
                        exp_display = f"{exp_score:.1f}" if exp_score is not None else exp
                    else:
                        majority_display = majority
                        exp_display = exp
                    correctness[key] = {
                        "predicted": majority_display, "expected": exp_display, "correct": ok
                    }
                correctness["score"] = f"{img_correct}/{len(standard_keys)}"
                print(f"  IMAGE SCORE: {img_correct}/{len(standard_keys)} keys correct")

            master_report["images_data"][filename] = {
                "successful_runs": successful_runs,
                "latency_stats": time_stats,
                "answer_distribution": image_summary,
                "correctness": correctness,
                "raw_runs": all_raw_results
            }
        else:
            print(f"Skipping report generation for {filename}: No successful runs.")

    timestamp = int(time.time())
    master_json_path = os.path.join(output_visual_dir, f"batch_report_{timestamp}.json")
    with open(master_json_path, "w") as f:
        json.dump(master_report, f, indent=2)

    master_report["overall_accuracy"] = (
        f"{overall_correct}/{overall_total} ({overall_correct / overall_total * 100:.1f}%)"
        if overall_total else "N/A (no ground truth)"
    )

    print("\n" + "="*50)
    print(f"BATCH COMPLETE. Visual reports and JSON saved to:\n{output_visual_dir}")
    if overall_total:
        print(f"OVERALL ACCURACY: {overall_correct}/{overall_total} "
              f"({overall_correct / overall_total * 100:.1f}%) across all runs with ground truth")
    print("="*50)


# --- Execution ---
if __name__ == "__main__":
    # GT (evaluation_ground_truth.json) is keyed by photo_1.jpg..photo_9.jpg,
    # which live in demo_phots_for_evaluation. Use that folder for correctness.
    target_folder = "/home/citic_lab/qwen3_museum/demo_phots_for_evaluation"
    # target_folder = "/home/dbek/src/qwen3-api-niki/Qwen3-Museum-Group-Interaction-API/demo_phots_for_evaluation_high_res"

    run_batch_evaluation(target_folder, iterations=10)
