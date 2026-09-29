import requests
import os
import json
import time


url = "http://127.0.0.1:5555/api/relations"
output_folder = "output_frames"
image_name = "frame_000.png" # Name of the picture in the output_frames


filename = os.path.join(output_folder, image_name)

if not os.path.exists(filename):
    print(f"ERROR: File '{filename}' was not found!")
    exit()

results = []
frame_count = "0000" # Static value for picture

data = {
    "message": {
        "text": "Describe the interaction with the guide",
        "files": [filename]
    }
}

try:
    res = requests.post(url, json=data) 
    
    if res.status_code == 200:
        raw_data = res.json()
        standard_keys = [
            "Age composition", "Spatial formation", 
            "Interpersonal spacing", "Interpersonal spacing", "Blue area positioning", "Engagement rating"
            ]
        processed_entry = {}
        if isinstance(raw_data, str):
            try:
                # Strip markdown if AI ignored the "No Markdown" rule
                clean_str = raw_data.replace("```json", "").replace("```", "").strip()
                raw_data = json.loads(clean_str)
            except:
                raw_data = {}

        if "results" in raw_data and isinstance(raw_data["results"], list):
            # Flatten the list if the AI sent a list of small dicts
            for part in raw_data["results"]:
                processed_entry.update(part)
        else:
            processed_entry = raw_data

        final_json = {key: processed_entry.get(key, "Not Observed") for key in standard_keys}
        final_json["frame_id"] = frame_count
        results.append(final_json)
    else:
        print(f"Error API: {res.status_code}")
        print(res.text)

except requests.exceptions.ConnectionError:
    print("ERROR: API not working")

if results:
    os.makedirs("output_json", exist_ok=True)
    timestamp = int(time.time())
    filename2 = f"output_json/relations_{timestamp}.json"

    with open(filename2, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Saved to → {filename2}")