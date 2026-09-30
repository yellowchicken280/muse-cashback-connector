#!/usr/bin/env python3
"""Muse Cashback Connector — multi-user trip ledger service.

Stdlib-only Python, no dependencies. Serves the trip-ledger API plus the
connector's own openapi.json and llms.txt, so a Muse user can build a custom
connector from a single URL.

Each user mints their own bearer token via POST /v1/link. Trip data is
isolated per token (only the SHA-256 hash is ever stored on disk). Users can
delete their own data via DELETE /v1/account.

Setup:
    python3 server.py              # listens on 0.0.0.0:8000 (PORT env to change)

Optional env:
    CASHBACK_LINK_SECRET   If set, POST /v1/link requires {"link_secret": ...}
                           matching it (private deployment). If unset, anyone
                           can mint a token (rate-limited) — suitable for a
                           public directory listing.
    CASHBACK_DATA_DIR      Data directory (default ./data).
    PORT                   Listen port (default 8000).

Then in Muse: "build a custom connector from https://YOUR-HOST/openapi.json".
Muse calls POST /v1/link to get the user's token, stores it in its secure
credential store, and uses it for all subsequent calls.

This ledger records what the agent did (cashback attribution armed). It does
not reflect Rakuten's records and never confirms cashback was credited.
"""

import hashlib
import json
import os
import secrets
import sys
import time
from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("CASHBACK_DATA_DIR", os.path.join(HERE, "data"))
USERS_DIR = os.path.join(DATA_DIR, "users")
LINK_SECRET = os.environ.get("CASHBACK_LINK_SECRET", "")
PORT = int(os.environ.get("PORT", "8000"))
VERSION = "0.2.0"

# Rate limits: (max_requests, window_seconds)
LINK_LIMIT = (10, 3600)      # token minting: 10/hour per IP
API_LIMIT = (120, 60)        # trip endpoints: 120/min per IP
_rate_buckets = {}


def rate_ok(key, limit):
    max_req, window = limit
    now = time.monotonic()
    bucket = _rate_buckets.setdefault(key, deque())
    while bucket and bucket[0] <= now - window:
        bucket.popleft()
    if len(bucket) >= max_req:
        return False
    bucket.append(now)
    return True


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def user_path(h):
    return os.path.join(USERS_DIR, h + ".json")


def load_user(h):
    p = user_path(h)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def save_user(h, data):
    os.makedirs(USERS_DIR, exist_ok=True)
    tmp = user_path(h) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, user_path(h))


def delete_user(h):
    p = user_path(h)
    if os.path.exists(p):
        os.remove(p)
        return True
    return False


MAXLEN = {"merchant": 200, "activated_rate": 100, "order_ref": 100,
          "currency": 10, "notes": 2000}


def validate_trip(body):
    if not isinstance(body, dict):
        return None, "invalid JSON body"
    trip = {}
    for field, maxlen in MAXLEN.items():
        val = body.get(field)
        if val is None:
            continue
        if not isinstance(val, str):
            return None, "%s must be a string" % field
        val = val.strip()
        if len(val) > maxlen:
            return None, "%s too long (max %d chars)" % (field, maxlen)
        trip[field] = val
    if not trip.get("merchant"):
        return None, "merchant is required"
    if not trip.get("activated_rate"):
        return None, "activated_rate is required"
    amount = body.get("amount")
    if amount is not None:
        if not isinstance(amount, (int, float)) or isinstance(amount, bool):
            return None, "amount must be a number"
        if amount < 0 or amount > 1000000:
            return None, "amount out of range"
        trip["amount"] = amount
    trip.setdefault("currency", "USD")
    return trip, None


class Handler(BaseHTTPRequestHandler):
    server_version = "CashbackConnector/" + VERSION

    # -- helpers ---------------------------------------------------------
    def _send_json(self, status, obj, extra_headers=None):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
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
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            length = 0
        if length > 65536:
            return None, "body too large"
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw or b"{}"), None
        except json.JSONDecodeError:
            return None, "invalid JSON"

    def _client_ip(self):
        # Behind Render's (or any) reverse proxy the socket peer is the proxy
        # itself, so every user would share one rate-limit bucket. Honor the
        # client IP the trusted proxy appends to X-Forwarded-For: the last
        # entry is the one the proxy added, so a client-supplied spoofed
        # entry to its left can't be selected.
        xff = self.headers.get("X-Forwarded-For", "")
        if xff:
            return xff.split(",")[-1].strip()
        return self.client_address[0]

    def _auth_user(self):
        """Returns (user_hash, user_data) or (None, None)."""
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None, None
        h = token_hash(auth[7:].strip())
        data = load_user(h)
        if data is None:
            return None, None
        return h, data

    # -- routing ----------------------------------------------------------
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
            if not rate_ok("api:" + self._client_ip(), API_LIMIT):
                self._send_json(429, {"error": "rate limited, try again later"},
                                {"Retry-After": "60"})
                return
            h, data = self._auth_user()
            if h is None:
                self._send_json(401, {"error": "missing or invalid bearer token"})
                return
            trips = sorted(data.get("trips", []),
                           key=lambda t: t["created_at"], reverse=True)
            self._send_json(200, {"trips": trips})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        route = urlparse(self.path).path
        if route == "/v1/link":
            if not rate_ok("link:" + self._client_ip(), LINK_LIMIT):
                self._send_json(429, {"error": "too many link requests, try again later"},
                                {"Retry-After": "3600"})
                return
            body, err = self._read_json()
            if err:
                self._send_json(400, {"error": err})
                return
            if LINK_SECRET:
                if body.get("link_secret") != LINK_SECRET:
                    self._send_json(403, {"error": "invalid link_secret"})
                    return
            token = "cbk_" + secrets.token_hex(24)
            h = token_hash(token)
            save_user(h, {"created_at": datetime.now(timezone.utc).isoformat(),
                          "trips": []})
            self._send_json(201, {"token": token})
            return
        if route == "/v1/trips":
            if not rate_ok("api:" + self._client_ip(), API_LIMIT):
                self._send_json(429, {"error": "rate limited, try again later"},
                                {"Retry-After": "60"})
                return
            h, data = self._auth_user()
            if h is None:
                self._send_json(401, {"error": "missing or invalid bearer token"})
                return
            body, err = self._read_json()
            if err:
                self._send_json(400, {"error": err})
                return
            trip, terr = validate_trip(body)
            if terr:
                self._send_json(400, {"error": terr})
                return
            trip["id"] = ("trip_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                          + "_" + secrets.token_hex(3))
            trip["created_at"] = datetime.now(timezone.utc).isoformat()
            data["trips"].append(trip)
            save_user(h, data)
            self._send_json(201, trip)
            return
        self._send_json(404, {"error": "not found"})

    def do_DELETE(self):
        route = urlparse(self.path).path
        if route == "/v1/account":
            if not rate_ok("api:" + self._client_ip(), API_LIMIT):
                self._send_json(429, {"error": "rate limited, try again later"},
                                {"Retry-After": "60"})
                return
            h, data = self._auth_user()
            if h is None:
                self._send_json(401, {"error": "missing or invalid bearer token"})
                return
            delete_user(h)
            self._send_json(200, {"deleted": True})
            return
        self._send_json(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    os.makedirs(USERS_DIR, exist_ok=True)
    print("Cashback connector v%s" % VERSION)
    if LINK_SECRET:
        print("Link mode: PRIVATE (CASHBACK_LINK_SECRET is set)")
    else:
        print("Link mode: OPEN (anyone can mint a token, rate-limited)")
    print("Serving on 0.0.0.0:%d  (data dir: %s)" % (PORT, DATA_DIR))
    print("Spec:  http://localhost:%d/openapi.json" % PORT)
    print("Guide: http://localhost:%d/llms.txt" % PORT)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
