#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Мини-клиент API amoCRM (Синдикат). Токен — в tools/amo_token.txt (не в git)."""
import json
import os
import time
import urllib.request

BASE = "https://syndicat.amocrm.ru/api/v4"
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "amo_token.txt")

PIPELINE_COLD = 11174702        # «Холодный обзвон»
STATUS_COLD_NEW = 87697006      # этап «Взят в работу»
USER_NIKITA = 10860218          # Сазонов Никита
CLOSED_STATUSES = {142, 143}    # Успех / Закрыто (одинаковы во всех воронках)


def _token():
    if os.environ.get("AMO_TOKEN"):
        return os.environ["AMO_TOKEN"].strip()
    with open(TOKEN_FILE) as f:
        return f.read().strip()


def request(method, path, payload=None, retries=3):
    url = BASE + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "Bearer " + _token(),
        "Content-Type": "application/json",
    })
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req) as r:
                body = r.read()
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            if e.code == 204:
                return {}
            if e.code == 429 and attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise RuntimeError("amoCRM %s %s -> %s: %s" % (method, path, e.code, e.read()[:300]))
    return {}


def get(path):
    return request("GET", path)


def post(path, payload):
    return request("POST", path, payload)


def paginate(path, key, params=""):
    """Итерация по всем страницам списка (limit=250)."""
    page = 1
    while True:
        sep = "&" if ("?" in path or params) else "?"
        q = "%s%s%slimit=250&page=%d" % (path, ("?" + params) if params else "", sep if not params else "&", page)
        try:
            d = request("GET", q)
        except RuntimeError as e:
            if "-> 204" in str(e):
                return
            raise
        items = (d.get("_embedded") or {}).get(key) or []
        if not items:
            return
        for it in items:
            yield it
        if not (d.get("_links") or {}).get("next"):
            return
        page += 1
        time.sleep(0.15)
