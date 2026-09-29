import argparse
import json
import os
import time
from pathlib import Path

from ollama import Client


client = Client(host="http://127.0.0.1:11434")
DEFAULT_MODEL = "qwen3-vl:8b"
DEFAULT_IMAGE = "/home/gpu-admin/stelios/Qwen3-Museum-Group-Interaction-API/demo_phots_for_evaluation/photo_1.jpg"
DEFAULT_NUM_PREDICT = 256

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


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--num-predict", type=int, default=DEFAULT_NUM_PREDICT)
    return parser.parse_args()


def _extract_json(text):
    cleaned = text.replace("```json", "").replace("```", "").strip()
    if not cleaned.startswith("{"):
        cleaned = "{" + cleaned
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    return json.loads(cleaned)


def process_single_image(image_path, model_name=None, num_predict=DEFAULT_NUM_PREDICT):
    if not os.path.exists(image_path):
        print(f"Error: File '{image_path}' not found.")
        return None

    started = time.time()
    try:
        response = client.chat(
            model=model_name or DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": "Describe the interaction with the guide", "images": [image_path]},
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
    except Exception as exc:
        print(f"Error calling Ollama: {exc}")
        return None

    latency = time.time() - started
    raw_data = response["message"]["content"] if "message" in response else ""

    try:
        parsed = _extract_json(raw_data)
    except json.JSONDecodeError:
        print(f"  [!] Could not parse JSON: {raw_data[:200]}")
        parsed = {}

    standard_keys = [
        "Age composition",
        "Spatial formation",
        "Interpersonal spacing",
        "Postural assessment",
        "Area positioning",
        "Engagement rating",
    ]
    final_json = {key: parsed.get(key, "Not Observed") for key in standard_keys}
    final_json["inference_time_seconds"] = round(latency, 2)
    return final_json


def main():
    args = parse_args()
    result = process_single_image(args.image, model_name=args.model, num_predict=args.num_predict)

    if result is None:
        raise SystemExit(f"Failed to process image: {args.image}")

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
