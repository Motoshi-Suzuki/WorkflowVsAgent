"""
Web UI server.

Usage:
  python app.py          # then open http://localhost:8080
"""

import json
import queue
import threading
import anthropic
from flask import Flask, Response, request, send_file, stream_with_context
from dotenv import load_dotenv
from scenarios import SCENARIOS
import workflow
import agent

load_dotenv()

app = Flask(__name__, static_folder="static")

_TRANSLATE_SYSTEM = (
    "Translate the following customer-service text into natural Japanese. "
    "Output only the translation — no explanation, no romanisation."
)


def _translate(client: anthropic.Anthropic, text: str) -> str:
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        temperature=0,
        system=_TRANSLATE_SYSTEM,
        messages=[{"role": "user", "content": text}],
    )
    return resp.content[0].text


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

    def make_notify(side: str, client: anthropic.Anthropic):
        def _emit(event_type: str, event_data: str) -> None:
            q.put({"side": side, "type": event_type, "data": event_data})
            if event_type == "reply":
                ja = _translate(client, event_data)
                q.put({"side": side, "type": "reply_ja", "data": ja})
        return _emit

    def worker():
        try:
            client = anthropic.Anthropic()
            inquiry_ja = _translate(client, inquiry)
            q.put({"type": "inquiry_ja", "data": inquiry_ja})
            workflow.run_workflow(inquiry, notify=make_notify("workflow", client))
            agent.run_agent(inquiry, notify=make_notify("agent", client))
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
