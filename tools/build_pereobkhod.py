#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пересобирает файлы переобхода pereobkhod-N.txt из актуального sitemap.xml.

Для Яндекс.Вебмастера («Индексирование → Переобход страниц»): вставляете список
URL пачками. Файлы по 140 ссылок. Приоритет — сверху: главная и разделы, затем
НОВЫЕ лендинги категорий /k/, затем карточки товаров.

Запуск:  python3 tools/build_pereobkhod.py
"""
import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITEMAP = os.path.join(ROOT, "sitemap.xml")
PER_FILE = 140

def main():
    xml = open(SITEMAP, encoding="utf-8").read()
    urls = re.findall(r"<loc>(.*?)</loc>", xml)

    top, landings, products, other = [], [], [], []
    for u in urls:
        if re.search(r"/(index\.html)?$", u) or u.endswith(("/catalog.html", "/uslugi.html", "/faq.html")):
            top.append(u)
        elif "/k/" in u:
            landings.append(u)
        elif "/p/" in u:
            products.append(u)
        else:
            other.append(u)

    ordered = top + landings + other + products
    # удалить старые файлы переобхода (в т.ч. помеченные «ок»)
    for f in os.listdir(ROOT):
        if re.match(r"pereobkhod-.*\.txt$", f):
            os.remove(os.path.join(ROOT, f))

    chunks = [ordered[i:i + PER_FILE] for i in range(0, len(ordered), PER_FILE)]
    for n, chunk in enumerate(chunks, 1):
        open(os.path.join(ROOT, f"pereobkhod-{n}.txt"), "w", encoding="utf-8").write(
            "\n".join(chunk) + "\n")

    print(f"всего URL: {len(ordered)} (топ {len(top)}, лендинги {len(landings)}, "
          f"товары {len(products)}, прочее {len(other)})")
    print(f"файлов переобхода: {len(chunks)} (по {PER_FILE})")
    print(f"первый батч: топ-страницы + все {len(landings)} лендингов идут первыми")

if __name__ == "__main__":
    main()
