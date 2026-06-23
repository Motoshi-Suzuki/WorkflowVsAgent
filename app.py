"""
Web UI server.

Usage:
  python app.py          # then open http://localhost:5000
"""

import json
import queue
import threading
from flask import Flask, Response, request, send_file, stream_with_context
from dotenv import load_dotenv
from scenarios import SCENARIOS
import workflow
import agent

load_dotenv()

app = Flask(__name__, static_folder="static")


@app.route("/")
def index():
    return send_file("static/index.html")


@app.route("/run", methods=["POST"])
def run():
    data = request.get_json(force=True)
    scenario = data.get("scenario", "").strip()
    custom = data.get("inquiry", "").strip()

    if scenario and scenario in SCENARIOS:
        inquiry = SCENARIOS[scenario]["inquiry"]
    elif custom:
        inquiry = custom
    else:
        return {"error": "provide a valid scenario or inquiry"}, 400

    q: queue.Queue = queue.Queue()

    def notify(side):
        def _emit(event_type, event_data):
            q.put({"side": side, "type": event_type, "data": event_data})
        return _emit

    def worker():
        try:
            workflow.run_workflow(inquiry, notify=notify("workflow"))
            agent.run_agent(inquiry, notify=notify("agent"))
        finally:
            q.put(None)

    threading.Thread(target=worker, daemon=True).start()

    @stream_with_context
    def generate():
        while True:
            item = q.get()
            if item is None:
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                break
            yield f"data: {json.dumps(item)}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    app.run(debug=True, port=8080, threaded=True)
