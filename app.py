import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()

from detection.combine import combine_signals, label_and_confidence, llm_to_p
from detection.labels import generate_transparency_message
from detection.llm_signal import classify_with_llm
from detection.stylometry import analyze_stylometry
import storage

app = Flask(__name__)
storage.init_db()

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

MAX_TEXT_LENGTH = 20000
MIN_APPEAL_REASONING_LENGTH = 10

ATTRIBUTION_LABELS = {
    "ai": "likely_ai",
    "human": "likely_human",
    "uncertain": "uncertain",
}


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@app.route("/submit", methods=["POST"])
@limiter.limit("10 per minute;100 per day")
def submit():
    body = request.get_json(silent=True) or {}
    text = body.get("text", "")
    creator_id = body.get("creator_id", "")
    title = body.get("title")

    if not text or not text.strip():
        return jsonify({"error": "text is required"}), 400
    if not creator_id or not creator_id.strip():
        return jsonify({"error": "creator_id is required"}), 400
    if len(text) > MAX_TEXT_LENGTH:
        return jsonify({"error": f"text exceeds {MAX_TEXT_LENGTH} character limit"}), 413

    llm_result = classify_with_llm(text)
    style_result = analyze_stylometry(text)

    p_llm = llm_to_p(llm_result)
    p_style = style_result["p_style"]
    p_combined, dampened = combine_signals(p_llm, p_style)
    label, confidence = label_and_confidence(p_combined, style_result["word_count"])
    attribution = ATTRIBUTION_LABELS[label]
    transparency_message = generate_transparency_message(label)

    content_id = str(uuid.uuid4())
    created_at = _now_iso()

    signals = {
        "llm": llm_result,
        "stylometry": style_result,
        "p_llm": round(p_llm, 4),
        "p_style": round(p_style, 4),
        "p_combined": round(p_combined, 4),
        "dampened": dampened,
    }

    storage.create_submission(
        content_id=content_id,
        creator_id=creator_id,
        title=title,
        text=text,
        attribution=attribution,
        confidence=confidence,
        transparency_message=transparency_message,
        status="classified",
        created_at=created_at,
        signals=signals,
    )

    storage.log_event(
        event_type="decision",
        content_id=content_id,
        timestamp=created_at,
        entry={
            "content_id": content_id,
            "creator_id": creator_id,
            "timestamp": created_at,
            "attribution": attribution,
            "confidence": confidence,
            "llm_score": round(p_llm, 4),
            "style_score": round(p_style, 4),
            "combined_score": round(p_combined, 4),
            "status": "classified",
        },
    )

    return (
        jsonify(
            {
                "content_id": content_id,
                "creator_id": creator_id,
                "attribution": attribution,
                "confidence": confidence,
                "label": transparency_message,
                "signals": signals,
            }
        ),
        201,
    )


@app.route("/appeal", methods=["POST"])
def appeal():
    body = request.get_json(silent=True) or {}
    content_id = body.get("content_id", "")
    creator_reasoning = body.get("creator_reasoning", "")

    if not content_id or not content_id.strip():
        return jsonify({"error": "content_id is required"}), 400
    if not creator_reasoning or len(creator_reasoning.strip()) < MIN_APPEAL_REASONING_LENGTH:
        return (
            jsonify(
                {
                    "error": f"creator_reasoning is required and must be at least {MIN_APPEAL_REASONING_LENGTH} characters"
                }
            ),
            400,
        )

    submission = storage.get_submission(content_id)
    if submission is None:
        return jsonify({"error": "submission not found"}), 404
    if submission["status"] == "under_review":
        return jsonify({"error": "an appeal is already under review for this submission"}), 409

    status_before = submission["status"]
    appeal_id = str(uuid.uuid4())
    submitted_at = _now_iso()

    storage.create_appeal(appeal_id, content_id, creator_reasoning, submitted_at)
    storage.update_submission_status(content_id, "under_review")

    storage.log_event(
        event_type="appeal",
        content_id=content_id,
        timestamp=submitted_at,
        entry={
            "content_id": content_id,
            "creator_id": submission["creator_id"],
            "timestamp": submitted_at,
            "appeal_id": appeal_id,
            "appeal_reasoning": creator_reasoning,
            "status_before": status_before,
            "status": "under_review",
        },
    )

    return (
        jsonify(
            {
                "appeal_id": appeal_id,
                "content_id": content_id,
                "status": "under_review",
                "message": "Your appeal has been recorded and this content is now marked under review.",
            }
        ),
        201,
    )


@app.route("/log", methods=["GET"])
def get_log():
    return jsonify({"entries": storage.get_log()})


if __name__ == "__main__":
    app.run(port=5000, debug=True)
