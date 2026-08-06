#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Синхронизация общей Google Таблицы с amoCRM.

Менеджеры с любого компьютера (Safari, Windows — неважно) вставляют строки
в общую Google Таблицу. Этот скрипт (запускается GitHub Actions каждый час)
скачивает таблицу как CSV и заливает НОВЫЕ номера в amoCRM:
компания + сделка «Холодный обзвон → Взят в работу» + задача на завтра.
Номера, уже существующие в amo, пропускаются — можно гнать хоть каждую
минуту, дублей не будет.

Ожидаемые колонки листа (порядок не важен, лишние игнорируются):
    Регион | Название | Телефон | Адрес | Сайт | Комментарий
Обязательные: Телефон и Название (или Регион — иначе тег «холодная база» без региона).

URL публикации CSV берётся из переменной окружения SHEET_CSV_URL
(Файл → Поделиться → Опубликовать в интернете → лист → CSV)
или из tools/sheet_url.txt.

Запуск руками: python3 tools/amo_sheet_sync.py
"""
import csv
import io
import os
import sys
import time
import urllib.request

from amo_api import TOKEN_FILE  # noqa: F401  (общий пакет tools/)
from azs_push_amo import create_entry, norm_phone, phone_exists, tomorrow_ts

URL_FILE = os.path.join(os.path.dirname(__file__), "sheet_url.txt")


def sheet_url():
    if os.environ.get("SHEET_CSV_URL"):
        return os.environ["SHEET_CSV_URL"].strip()
    if os.path.exists(URL_FILE):
        with open(URL_FILE) as f:
            return f.read().strip()
    sys.exit("Нет ссылки на таблицу: задайте SHEET_CSV_URL или создайте tools/sheet_url.txt")


def fetch_rows(url):
    with urllib.request.urlopen(url) as r:
        text = r.read().decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return []
    header = [h.strip().lower() for h in rows[0]]

    def col(*names):
        for n in names:
            if n in header:
                return header.index(n)
        return None

    i_phone = col("телефон", "phone")
    i_name = col("название", "компания", "name")
    i_region = col("регион", "город", "region")
    i_addr = col("адрес", "address")
    i_site = col("сайт", "web")
    i_comment = col("комментарий", "примечание", "comment")
    if i_phone is None:
        sys.exit("В таблице нет колонки «Телефон» (первая строка листа — заголовки)")

    out = []
    for row in rows[1:]:
        def cell(i):
            return row[i].strip() if i is not None and i < len(row) else ""
        out.append({
            "phone": cell(i_phone),
            "name": cell(i_name),
            "region": cell(i_region),
            "addr": cell(i_addr),
            "site": cell(i_site),
            "comment": cell(i_comment),
        })
    return out


def main():
    rows = fetch_rows(sheet_url())
    print("строк в таблице:", len(rows))

    companies = {}   # phone -> запись (дедуп внутри таблицы)
    for r in rows:
        phone = norm_phone(r["phone"])
        if not phone:
            continue
        c = companies.setdefault(phone, {
            "name": r["name"] or phone, "type": "", "brand": "", "head": "",
            "addrs": [], "site": r["site"], "comment": r["comment"],
            "region": r["region"] or "без региона",
        })
        if r["addr"] and r["addr"] not in c["addrs"]:
            c["addrs"].append(r["addr"])

    due_ts = tomorrow_ts()
    created = skipped = 0
    for phone, c in companies.items():
        if phone_exists(phone):
            skipped += 1
            continue
        lead_id = create_entry(phone, c, c["region"], due_ts)
        created += 1
        print("  создано: %s %s (сделка %d)" % (c["name"], phone, lead_id))
        time.sleep(0.25)

    print("итого: новых %d, уже были в amo %d" % (created, skipped))


if __name__ == "__main__":
    main()
