import base64
import io
import json
import os
import time

from PIL import Image
from ollama import Client


client = Client(host="http://127.0.0.1:11434")
DEFAULT_MODEL_NAME = os.getenv("MUSEUM_MODEL", "qwen3.5:9b")
MODEL_OPTIONS = {
    "keep_alive": -1,
    "num_predict": 1000,
    "temperature": 0.1,
    "top_k": 50,
    "top_p": 0.5,
}

ANALYSIS_LABELS = {
    "Spatial formation": [
        "In a Row",
        "Not in a Row",
        "Not Observed",
    ],
    "Interpersonal spacing": [
        "Close",
        "Separated",
        "Not Observed",
    ],
    "Postural assessment": [
        "Standing Only",
        "Mixed (Standing/Seated)",
        "Sitting Only",
        "Not Observed",
    ],
    "Area positioning": [
        "Inside Area",
        "Outside Area",
        "Mixed/On Boundary",
        "No Area Visible",
        "Not Observed",
    ],
    "Engagement rating": [
        "High Engagement",
        "Moderate Engagement",
        "Low Engagement",
        "Passive/Observation Only",
        "Not Observed",
    ],
}


SYSTEM_PROMPT = """Classify the main foreground group in the image. Work from visible evidence only.

Before answering, silently make one left-to-right list of the participating people. Include foreground people taking part inside, on, or immediately beside the marked floor area. Do not exclude a fully visible foreground participant merely because that person is detached from the others or outside the boundary. Exclude bystanders who are occupied with a separate activity even when they are visible nearby, distant background people, reflections, pictures, and unconnected cropped edge figures. Use the same people for all six fields.

For each listed person, silently note:
1. standing or seated;
2. floor anchor: shoes for standing, pelvis/seat/lower-torso support for seated or reclining;
3. nearest upper-body gap;
4. attention toward the camera or a guide/presenter near the camera: attentive, distracted, or uncertain.

Decide each field independently:

Area positioning:
- First locate the complete marked floor region before judging any person. It is the interior enclosed by a coherent closed boundary such as tape, paint, stripes, or another line. It can have any color, shape, size, or camera perspective. A short hidden section may be inferred only when the visible edges clearly continue the same closed boundary.
- Ignore unrelated colored objects, open lines, floor patterns, tile seams, shadows, cables, furniture edges, and equipment. If several markings are visible, do not merge them or substitute another outline: use the one closed floor region relevant to the participant group.
- Mentally mark a point near the center of the enclosed floor region. For each participant, compare the floor anchor with every boundary edge. The anchor is inside only when it lies toward the region center rather than beyond an edge. In particular, an anchor beyond the visually far edge of the region is outside even if the person's body overlaps the region in the image.
- For standing people use the shoe-to-floor contact location, not the torso. For seated or reclining people use the pelvis, seat, or lower-torso support location; legs and feet extending across the boundary do not make the person inside. A floor anchor on the boundary counts as inside.
- Count every listed participant, including participants immediately outside the boundary. Count people, not visible body area. Silently assign each participant either inside or outside, then verify that inside plus outside equals the participant total.
- Output inside divided by participant total as a numeric decimal from 0 to 1. Never output an area category word or inside/outside text.

Spatial formation:
- Compare both left-right position and image depth of the floor anchors.
- In a Row: nearly all anchors form one recognizable side-by-side line at similar depth, or one recognizable front-to-back line at similar lateral position. Perspective may make that line diagonal, and small stance/seat offsets are acceptable. A clearly displaced anchor more than about one body-depth from the shared band makes the whole arrangement Not in a Row.
- Not in a Row: anchors are staggered in both lateral position and depth, or form a cluster, arc, circle, V, multiple lines, or open-center arrangement. Two arbitrary points at different lateral positions and depths are not automatically a row merely because a mathematical line can connect them.
- A group facing the camera is not automatically a row. Judge all anchors, not one aligned subgroup. Body direction and spacing do not decide this field.

Interpersonal spacing:
- Inspect clear air between neighboring shoulder/torso contours at comparable depth.
- Close is a strict label: choose it only when the entire group is visibly compact and almost every neighboring upper body touches, overlaps, or has a gap smaller than about one torso width. Touching is not required, but no participant may be clearly detached.
- Separate: choose it when clear shoulder-level air divides people, a torso could fit in an important gap, any participant is detached, or open floor separates parts of the group.
- Do not label the whole group Close because one pair or seated subgroup is close. Judge shoulder/torso gaps for every participant, not feet or extended legs.

Postural assessment:
- Standing Only: all listed people stand.
- Sitting Only: all listed people sit on a chair or floor; reclining on the floor also counts as seated.
- Mixed (Standing/Seated): at least one listed person stands and at least one sits.

Engagement rating:
- Engagement means attention or response toward the camera or a guide/presenter near it. Peer conversation and unrelated actions do not count.
- Attentive requires positive evidence such as directed face/head and gaze, responsive gesture, or a deliberate ready/posed stance.
- Distracted includes looking down, turning away, focusing on an unrelated phone/object/action, or attending to peers instead.
- Uncertain orientation does not count as attentive.
- Count attentive, distracted, and uncertain people before choosing the label.
- High Engagement is strict: at least about 80% must show unmistakable deliberate attention, any remainder may only be uncertain, and nobody may be clearly distracted. Several roughly frontal faces are not enough.
- Low Engagement: attentive people are half or fewer and any strong distraction is visible; or roughly one-third or more of the group is strongly distracted. Strong distraction includes looking down at a phone/object, turning the back to the camera/guide, or performing an unrelated task.
- Moderate Engagement: use it between those cases, when a majority is attentive but attention is incomplete, casual, divided, or uncertain. An exactly half-attentive group can be Moderate when the remainder are neutral/uncertain rather than strongly distracted.
- A brief neutral glance toward a peer may be uncertain rather than strongly distracted.
- Low Engagement also applies when attention is visibly fragmented across unrelated directions/actions and there is no dominant shared focus on the camera/guide.
- Passive/Observation Only is for a group that clearly watches the camera/guide or presented subject but only observes/waits without active response or deliberate posing.
- Do not infer engagement from posture, formation, spacing, age, or group size.

Allowed categorical values:
- Spatial formation: In a Row, Not in a Row, Not Observed
- Interpersonal spacing: Close, Separate, Not Observed
- Postural assessment: Standing Only, Mixed (Standing/Seated), Sitting Only, Not Observed
- Engagement rating: High Engagement, Moderate Engagement, Low Engagement, Passive/Observation Only, Not Observed

Return only this raw JSON object. No reasoning, markdown, or extra keys:
{
"Area positioning": "...",
"Spatial formation": "...",
"Interpersonal spacing": "...",
"Postural assessment": "...",
"Engagement rating": "..."
}"""


def encode_image_to_base64(path):
    with Image.open(path) as img:
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")


def normalize_analysis(raw_data):
    if isinstance(raw_data, str):
        try:
            raw_data = json.loads(raw_data.replace("```json", "").replace("```", "").strip())
        except json.JSONDecodeError:
            return {field: "Not Observed" for field in ANALYSIS_LABELS}

    if not isinstance(raw_data, dict):
        return {field: "Not Observed" for field in ANALYSIS_LABELS}

    if "results" in raw_data and isinstance(raw_data["results"], list):
        merged = {}
        for result in raw_data["results"]:
            if isinstance(result, dict):
                merged.update(result)
        raw_data = merged

    final = {}
    for field in ANALYSIS_LABELS:
        value = raw_data.get(field, "Not Observed")
        if value is None or value == "":
            value = "Not Observed"
        final[field] = value
    return final


def _extract_json(text):
    cleaned = text.replace("```json", "").replace("```", "").strip()
    if not cleaned.startswith("{"):
        cleaned = "{" + cleaned
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    return json.loads(cleaned)


def generate(payload):
    base_text = payload["message"]["text"]
    image_path = payload["message"]["files"][0]
    previous_state = payload["message"].get("previous_state", None)
    model_name = payload["message"].get("model", DEFAULT_MODEL_NAME)

    img_b64 = encode_image_to_base64(image_path)
    user_prompt = base_text
    if previous_state:
        user_prompt += f"\n\n--- PREVIOUS FRAME STATE ---\n{json.dumps(previous_state, indent=2)}\n\nPlease maintain consistency with this state unless clear visual evidence dictates a change."

    response = client.chat(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt, "images": [img_b64]},
            {"role": "assistant", "content": "{"},
        ],
        options=MODEL_OPTIONS,
    )

    raw_string = response.message.content if hasattr(response, "message") else ""
    try:
        parsed = _extract_json(raw_string)
    except json.JSONDecodeError:
        parsed = {}

    final = normalize_analysis(parsed)
    return final
