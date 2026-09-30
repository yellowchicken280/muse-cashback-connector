#!/usr/bin/env python3
"""Muse Cashback Connector — trip ledger service.

Stdlib-only Python. Serves the trip-ledger API plus the connector's own
openapi.json and llms.txt, so a Muse user can build a custom connector from a
single URL.

Setup:
    export CASHBACK_CONNECTOR_TOKEN="$(openssl rand -hex 32)"  # or let it generate one
    python3 server.py              # listens on 0.0.0.0:8000 (PORT env to change)

Then in Muse: "build a custom connector from https://YOUR-HOST/openapi.json,
bearer token is <token>".

Data is stored as JSON in ./data (CASHBACK_DATA_DIR to change). This ledger
records what the agent did (cashback attribution armed). It does not reflect
Rakuten's records and never confirms cashback was credited.
"""

import json
import os
import secrets
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("CASHBACK_DATA_DIR", os.path.join(HERE, "data"))
TRIPS_FILE = os.path.join(DATA_DIR, "trips.json")
TOKEN_FILE = os.path.join(DATA_DIR, ".token")
PORT = int(os.environ.get("PORT", "8000"))
VERSION = "0.1.0"


def get_token():
    token = os.environ.get("CASHBACK_CONNECTOR_TOKEN")
    if token:
        return token, False
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            return f.read().strip(), False
    token = secrets.token_hex(32)
    with open(TOKEN_FILE, "w") as f:
        f.write(token)
    os.chmod(TOKEN_FILE, 0o600)
    return token, True


BEARER_TOKEN, TOKEN_GENERATED = get_token()


def load_trips():
    if not os.path.exists(TRIPS_FILE):
        return []
    with open(TRIPS_FILE) as f:
        return json.load(f)


def save_trips(trips):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = TRIPS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(trips, f, indent=2)
    os.replace(tmp, TRIPS_FILE)


class Handler(BaseHTTPRequestHandler):
    server_version = "CashbackConnector/" + VERSION

    def _send_json(self, status, obj):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path, content_type):
        full = os.path.join(HERE, path)
        if not os.path.exists(full):
            self._send_json(404, {"error": "not found"})
            return
        with open(full, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self):
        auth = self.headers.get("Authorization", "")
        return auth == "Bearer " + BEARER_TOKEN

    def do_GET(self):
        route = urlparse(self.path).path
        if route == "/v1/status":
            self._send_json(200, {"ok": True, "service": "muse-cashback-connector",
                                  "version": VERSION})
        elif route == "/openapi.json":
            self._send_file("openapi.json", "application/json")
        elif route == "/llms.txt":
            self._send_file("llms.txt", "text/plain; charset=utf-8")
        elif route == "/v1/trips":
            if not self._authorized():
                self._send_json(401, {"error": "missing or invalid bearer token"})
                return
            trips = load_trips()
            trips_sorted = sorted(trips, key=lambda t: t["created_at"], reverse=True)
            self._send_json(200, {"trips": trips_sorted})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        route = urlparse(self.path).path
        if route != "/v1/trips":
            self._send_json(404, {"error": "not found"})
            return
        if not self._authorized():
            self._send_json(401, {"error": "missing or invalid bearer token"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            length = 0
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid JSON"})
            return
        merchant = (body.get("merchant") or "").strip()
        rate = (body.get("activated_rate") or "").strip()
        if not merchant:
            self._send_json(400, {"error": "merchant is required"})
            return
        if not rate:
            self._send_json(400, {"error": "activated_rate is required"})
            return
        trip = {
            "id": "trip_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                   + "_" + secrets.token_hex(3),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "merchant": merchant,
            "activated_rate": rate,
        }
        for field in ("order_ref", "amount", "currency", "notes"):
            if body.get(field) is not None:
                trip[field] = body[field]
        if "currency" not in trip:
            trip["currency"] = "USD"
        trips = load_trips()
        trips.append(trip)
        save_trips(trips)
        self._send_json(201, trip)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    if TOKEN_GENERATED:
        print("Generated bearer token (saved to %s):" % TOKEN_FILE)
        print("  %s" % BEARER_TOKEN)
        print("Keep it secret — it's the only credential for your trip ledger.\n")
    print("Serving on 0.0.0.0:%d  (data dir: %s)" % (PORT, DATA_DIR))
    print("Spec:  http://localhost:%d/openapi.json" % PORT)
    print("Guide: http://localhost:%d/llms.txt" % PORT)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
