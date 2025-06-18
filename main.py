
from flask import Flask, request, jsonify
import openai
import os

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

ASSISTANT_ID = "asst_DEINEID"
THREAD_ID = "thread_DEINEID"

@app.route("/log_conversation", methods=["POST"])
def log_conversation():
    data = request.get_json()
    summary = data.get("summary", "")
    topic = data.get("topic", "Ohne Titel")

    if not summary:
        return jsonify({"error": "summary fehlt"}), 400

    try:
        openai.beta.threads.messages.create(
            thread_id=THREAD_ID,
            role="user",
            content=f"📌 Thema: {topic}\n\n💬 Zusammenfassung:\n{summary}"
        )
        return jsonify({"status": "OK", "message": "Gespeichert."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
