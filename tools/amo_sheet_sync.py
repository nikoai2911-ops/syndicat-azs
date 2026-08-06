#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Синхронизация общей Google Таблицы «Базы» с amoCRM.

Менеджеры парсят со своих компьютеров в общую таблицу (один лист = один
регион; сводные листы с колонкой «Регион» тоже поддерживаются). Скрипт
скачивает документ целиком (export xlsx) и заливает в amoCRM все НОВЫЕ
номера: компания (телефон, email, адрес, сайт, заметки менеджера в
примечании) + сделка «Холодный обзвон → Взят в работу» + задача на завтра.

Дедупликация по телефону: номера, уже существующие в amo, пропускаются,
поэтому запуск идемпотентен — хоть каждый час, дублей не будет.
Строки без телефона игнорируются (звонить некуда).

Ссылка на таблицу: env SHEET_URL (или tools/sheet_url.txt) — обычная ссылка
из адресной строки; таблица должна быть доступна «всем, у кого есть ссылка».

Запуск руками: python3 tools/amo_sheet_sync.py
GitHub Actions гоняет его каждый час (.github/workflows/amo-sheet-sync.yml).
"""
import io
import os
import re
import sys
import time
import urllib.request

from azs_push_amo import create_entry, norm_phone, phone_exists, tomorrow_ts

URL_FILE = os.path.join(os.path.dirname(__file__), "sheet_url.txt")
SERVICE_SHEETS_WITH_REGION_COL = True  # листы без колонки «Регион» берут регион из названия листа


def sheet_id():
    url = os.environ.get("SHEET_URL", "").strip()
    if not url and os.path.exists(URL_FILE):
        with open(URL_FILE) as f:
            url = f.read().strip()
    if not url:
        sys.exit("Нет ссылки: задайте SHEET_URL или создайте tools/sheet_url.txt")
    m = re.search(r"/spreadsheets/d/([A-Za-z0-9_\-]+)", url)
    return m.group(1) if m else url  # можно передать и голый id


def download_xlsx(sid):
    url = "https://docs.google.com/spreadsheets/d/%s/export?format=xlsx" % sid
    with urllib.request.urlopen(url) as r:
        return io.BytesIO(r.read())


def rows_from_workbook(buf):
    """Все листы -> записи {phone, name, region, addr, site, email, comment}."""
    import openpyxl
    wb = openpyxl.load_workbook(buf, read_only=True)
    for ws in wb.worksheets:
        rows = ws.iter_rows(values_only=True)
        try:
            header = [str(h).strip().lower() if h else "" for h in next(rows)]
        except StopIteration:
            continue

        def col(*names):
            for n in names:
                if n in header:
                    return header.index(n)
            return None

        i_phone = col("телефон")
        i_name = col("название")
        if i_phone is None or i_name is None:
            continue  # служебный лист
        i_region = col("регион")
        i_addr = col("адрес")
        i_site = col("сайт")
        i_email = col("email", "почта")
        i_type = col("тип")
        i_brand = col("сеть", "бренд")
        i_status = col("статус")
        i_notes = col("заметки", "комментарий", "примечание")

        for row in rows:
            def cell(i):
                v = row[i] if i is not None and i < len(row) else None
                return str(v).strip() if v is not None else ""
            phone = norm_phone(cell(i_phone))
            if not phone:
                continue
            comment_bits = [b for b in (cell(i_status), cell(i_notes)) if b]
            yield {
                "phone": phone,
                "name": cell(i_name) or phone,
                "region": cell(i_region) or ws.title.strip(),
                "addr": cell(i_addr),
                "site": cell(i_site),
                "email": cell(i_email),
                "type": cell(i_type),
                "brand": cell(i_brand),
                "comment": " | ".join(comment_bits),
            }


def main():
    buf = download_xlsx(sheet_id())
    companies = {}
    total = 0
    for r in rows_from_workbook(buf):
        total += 1
        c = companies.setdefault(r["phone"], {
            "name": r["name"], "type": r["type"], "brand": r["brand"],
            "head": "", "addrs": [], "site": r["site"],
            "comment": r["comment"], "region": r["region"],
        })
        if r["addr"] and r["addr"] not in c["addrs"]:
            c["addrs"].append(r["addr"])
        if c["name"].lower() in ("без названия", "азс", "агзс") and \
                r["name"].lower() not in ("без названия", "азс", "агзс"):
            c["name"] = r["name"]
    print("строк с телефоном: %d | уникальных номеров: %d" % (total, len(companies)))

    due_ts = tomorrow_ts()
    created = skipped = 0
    for phone, c in companies.items():
        if phone_exists(phone):
            skipped += 1
            continue
        lead_id = create_entry(phone, c, c["region"], due_ts)
        created += 1
        print("  создано: %s [%s] %s (сделка %d)" % (c["name"], c["region"], phone, lead_id))
        time.sleep(0.25)
    print("итого: новых %d, уже были в amo %d" % (created, skipped))


if __name__ == "__main__":
    main()
