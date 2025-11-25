from flask import Flask, render_template, jsonify
import threading, os, json
import tracker  # your script runs in background

app = Flask(__name__)

# Start tracker in background
threading.Thread(target=tracker.main, daemon=True).start()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/status")
def status():
    return jsonify({"status": "Tracker is running"})

@app.route("/data")
def data():
    # Read the storage file if it exists and return it
    storage_file = os.path.join(os.getcwd(), "gme_ultimate_tracker.json")
    if os.path.exists(storage_file):
        try:
            with open(storage_file, 'r') as f:
                data = json.load(f)
            return jsonify({"ok": True, "data": data})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)})
    else:
        return jsonify({"ok": False, "error": "no storage file yet"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
