from flask import Flask, request, jsonify
from flask_cors import CORS
from ai_engine import generate

app = Flask(__name__)
CORS(app)

@app.route("/api/relations", methods=["POST"])
def relations():
    data = request.json
    try:
        response_dict = generate(data)
        return jsonify(response_dict), 200
    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5555)