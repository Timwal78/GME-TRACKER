from flask import Flask, render_template
import threading
import tracker  # your script runs in background

app = Flask(__name__)

# --------------------------
# BACKGROUND THREAD STARTUP
# --------------------------
threading.Thread(target=tracker.main, daemon=True).start()

# --------------------------
# FRONTEND ROUTE
# --------------------------
@app.route("/")
def home():
    return render_template("index.html")

# --------------------------
# SIMPLE STATUS ENDPOINT
# --------------------------
@app.route("/status")
def status():
    return {"status": "Tracker is running"}

# --------------------------
# RENDER-FRIENDLY SERVER
# --------------------------
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))  # REQUIRED on Render
    app.run(host="0.0.0.0", port=port)
