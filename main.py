from flask import Flask, request, jsonify
import openai
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

ASSISTANT_ID = "asst_GivBrU2QUfZquaLLWgDX4mko"
THREAD_ID = "thread_0wH4XtKM4IMbUCIGvyMMb7jC"

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

# === GET: Status-Seite für "/" ===
@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "message": "🟢 Assistant API ist live.",
        "endpoints": ["/log_conversation", "/read_external_sheet", "/read_all_sheets", "/query_sheet"]
    })

# === POST: Loggt GPT-Zusammenfassung in Assistant + Sheet A ===
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
            content=f"📌 Thema: {topic}\n\n📒 Zusammenfassung:\n{summary}"
        )

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

# === GET: Liest Daten aus einem definierten Tabellenblatt ===
@app.route("/read_external_sheet", methods=["GET"])
def read_external_sheet():
    try:
        result = sheet_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID_READ,
            range="A1:Z1000"
        ).execute()

        values = result.get("values", [])
        return jsonify({"status": "OK", "data": values}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === GET: Liest alle Datenblätter mit Inhalten aus dem Sheet ===
@app.route("/read_all_sheets", methods=["GET"])
def read_all_sheets():
    try:
        metadata = sheet_service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID_READ).execute()
        sheet_titles = [sheet["properties"]["title"] for sheet in metadata["sheets"]]

        all_data = {}
        for title in sheet_titles:
            result = sheet_service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID_READ,
                range=f"{title}!A1:Z1000"
            ).execute()
            all_data[title] = result.get("values", [])

        return jsonify({"status": "OK", "sheets": all_data}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === POST: GPT-Query mit Sheets-Daten füttern ===
@app.route("/query_sheet", methods=["POST"])
def query_sheet():
    try:
        metadata = sheet_service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID_READ).execute()
        sheet_titles = [sheet["properties"]["title"] for sheet in metadata["sheets"]]

        all_data = {}
        for title in sheet_titles:
            result = sheet_service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID_READ,
                range=f"{title}!A1:Z1000"
            ).execute()
            all_data[title] = result.get("values", [])

        # Sheets-Daten als Text zusammenstellen
        full_text = ""
        for title, rows in all_data.items():
            full_text += f"\n\nTabellenblatt: {title}\n"
            for row in rows:
                full_text += ", ".join(row) + "\n"

        # Prompt für GPT
        query = request.get_json().get("query", "")
        if not query:
            return jsonify({"error": "query fehlt"}), 400

        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Du analysierst strukturiert Google-Sheets-Daten."},
                {"role": "user", "content": f"Hier sind die Daten:\n{full_text}\n\nFrage: {query}"}
            ]
        )

        return jsonify({"status": "OK", "response": completion.choices[0].message["content"]}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === App-Start ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
