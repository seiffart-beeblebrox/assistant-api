from flask import Flask, request, jsonify
import openai
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

ASSISTANT_ID = "asst_GivBrU2QUfZquaLLWgDX4mko"
THREAD_ID = "thread_avg0ko6IsprGU3Aqd7KJYI55"

# === Google Sheets Setup ===
SERVICE_ACCOUNT_FILE = "/etc/secrets/google-credentials.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
sheet_service = build("sheets", "v4", credentials=creds)

# === Sheet IDs ===
SPREADSHEET_ID_WRITE = "1w2YfLfTq1D67GaL7y29eNlVELVz4_gcW7aIRzhd51u8"
SPREADSHEET_ID_READ = "1SAK36NbKQjMipJyZt4jarp4nT01DwIxxdpyxtyH2nDQ"
SHEET_RANGE_WRITE = "2025!A1"

# === POST: Loggt GPT-Zusammenfassung in Assistant + Sheet A ===
@app.route("/log_conversation", methods=["POST"])
def log_conversation():
    data = request.get_json()
    summary = data.get("summary", "")
    topic = data.get("topic", "Ohne Titel")

    if not summary:
        return jsonify({"error": "summary fehlt"}), 400

    try:
        # In GPT-Thread posten
        openai.beta.threads.messages.create(
            thread_id=THREAD_ID,
            role="user",
            content=f"📌 Thema: {topic}\n\n🗒️ Zusammenfassung:\n{summary}"
        )

        # In Sheet A schreiben
        values = [[topic, summary]]
        sheet_service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID_WRITE,
            range=SHEET_RANGE_WRITE,
            valueInputOption="RAW",
            body={"values": values}
        ).execute()

        return jsonify({"status": "OK", "message": "Gespeichert."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === GET: Liest alle Daten aus Sheet B ===
@app.route("/read_external_sheet", methods=["GET"])
def read_external_sheet():
    try:
        result = sheet_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID_READ,
            range="A1:Z1000"  # liest 1000 Zeilen und bis Spalte Z – praktisch "alles"
        ).execute()

        values = result.get("values", [])
        return jsonify({"status": "OK", "data": values}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === App-Start ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
