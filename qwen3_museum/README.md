Qwen3-Museum-Group-Interaction-API

This project uses a Vision-Language Model (LVLM) to analyze group behavior in museum settings. It extracts demographic data, spatial formations, and engagement levels from images or video frames using a highly constrained system prompt.

Features
- Vision-AI Analysis: Uses Qwen-series models to interpret complex human group dynamics.
- Strict JSON Output: Returns structured data ready for database insertion or real-time dashboards.
- Flask API: A lightweight REST interface to send images and receive behavior metrics.


### Installation

conda env create -f environment.yml
conda activate qwen3-api
conda install OpenCV

### Install Ollama (if not already installed)
curl -fsSL https://ollama.com/install.sh | sh

### Pull a vision model
Recommended model:

```bash
ollama pull qwen3-vl:8b
```

Run the API

### Running the API Server
python app.py

### Evaluation helpers

The repository includes a small evaluation set in `demo_phots_for_evaluation/`.
The frame-level ground truth is stored in `evaluation_ground_truth.json`.

Use the direct runners when you want Ollama called from the script itself:

```bash
python single_frame_qwen.py --image demo_phots_for_evaluation/photo_1.jpg
python batch_evaluate_qwen.py
```

Use the Flask-backed runners when you want the `app.py` path:

```bash
python app.py
python single_frame_qwen_using_api.py --image demo_phots_for_evaluation/photo_1.jpg
python batch_evaluate_qwen_using_api.py --folder demo_phots_for_evaluation
```

`single_frame_qwen_using_api.py` defaults to `qwen3-vl:8b` for quick tests.
`batch_evaluate_qwen_using_api.py` defaults to `qwen3.5:27b` for the heavier evaluation run.
Both scripts accept `--model` if you want to override that choice.

If you want the Flask-backed batch runner to use the 27B model, start the server with:

```bash
MUSEUM_MODEL=qwen3.5:27b python app.py
```

To unload the LVLM from the GPU:

```bash
curl http://localhost:11434/api/generate -d '{"model": "qwen3.5:27b", "keep_alive": 0}'
```
