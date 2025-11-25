from flask import Flask
import threading
import tracker  # runs your script

app = Flask(__name__)

@app.route("/")
def home():
    return "GME Ultimate Tracker is running!"

threading.Thread(target=tracker.main, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
