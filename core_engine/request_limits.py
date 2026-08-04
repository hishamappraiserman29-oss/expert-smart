"""Request-size and array-field validation helpers for Wave 4B1."""
from __future__ import annotations

import json
from typing import Any

from flask import request, jsonify


def read_bounded_json(max_bytes: int):
    """Read and parse the request body up to max_bytes.

    Returns (data, None) on success.
    Returns (None, flask Response) when validation fails — caller must return
    the response immediately.

    Steps:
    1. Reject declared Content-Length above limit before reading.
    2. Perform a single bounded read from request.stream.
    3. Return 413 for oversized data.
    4. Return 400 for empty data.
    5. Deserialize with json.loads directly.
    6. Return 400 for malformed JSON or encoding errors.
    Never calls request.get_json(), request.data, or request.get_data().
    """
    content_length = request.content_length
    if content_length is not None and content_length > max_bytes:
        return None, (jsonify({"error": "payload_too_large"}), 413)

    raw = request.stream.read(max_bytes + 1)

    if len(raw) > max_bytes:
        return None, (jsonify({"error": "payload_too_large"}), 413)

    if not raw:
        return None, (jsonify({"error": "json_body_required"}), 400)

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, (jsonify({"error": "invalid_json"}), 400)

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None, (jsonify({"error": "invalid_json"}), 400)

    return data, None


def check_array_field(data: Any, field: str, maximum: int):
    """Validate that *field* in *data* is a list not exceeding *maximum* items.

    Returns None when the field is absent or valid.
    Returns a flask Response when validation fails — caller must return it immediately.

    Rules:
    - Field absent: no error.
    - Field present but not a list: 400 invalid_array_field.
    - Field present, is a list, but len > maximum: 413 too_many_items.
    """
    value = data.get(field) if isinstance(data, dict) else None
    if value is None:
        return None
    if not isinstance(value, list):
        return jsonify({"error": "invalid_array_field", "field": field}), 400
    if len(value) > maximum:
        return jsonify({"error": "too_many_items", "field": field, "maximum": maximum}), 413
    return None


def accepted_uploaded_files(files, *, prefix: str | None = None) -> list:
    """Return all non-empty uploaded file objects from a Flask MultiDict.

    If prefix is given, only keys starting with that prefix are considered.
    Repeated multipart field names (same key sent multiple times) are each
    counted individually via files.getlist(key).
    """
    accepted = []
    for key in files.keys():
        if prefix is not None and not key.startswith(prefix):
            continue
        for uploaded in files.getlist(key):
            if uploaded and uploaded.filename:
                accepted.append(uploaded)
    return accepted
