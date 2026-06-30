# -*- coding: utf-8 -*-
"""
Генератор SEO-страниц товаров для SYNDICAT.
Читает catalog-data.js, создаёт:
  - p/<slug>.html        — отдельная страница на каждый товар (представитель группы)
  - assets/product.css   — общие стили страниц товаров
  - sitemap.xml          — карта сайта (главная, каталог, все товары)
  - catalog-data.js       — переписывает, добавляя каждому товару слаг "u"
Запуск:  python3 tools/build_seo.py
"""
import json, os, re, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://sd-kt.ru"
DATA = os.path.join(ROOT, "catalog-data.js")

SECROOT = {"azs": "toplivorazdatochnoe-oborudovanie", "agzs": "gazorazdatochnoe-oborudovanie"}

TR = {
 'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e','ж':'zh','з':'z','и':'i',
 'й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t',
 'у':'u','ф':'f','х':'h','ц':'c','ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'',
 'э':'e','ю':'yu','я':'ya'
}

def slugify(s):
    s = (s or "").lower()
    out = []
    for ch in s:
        if ch in TR: out.append(TR[ch])
        elif ch.isalnum() and ch.isascii(): out.append(ch)
        else: out.append('-')
    s = ''.join(out)
    s = re.sub(r'-+', '-', s).strip('-')
    return s[:70].strip('-') or 'tovar'

def esc(s):
    return html.escape(s or "", quote=True)

def load():
    raw = open(DATA, encoding='utf-8').read().strip()
    raw = raw[raw.index('=')+1:].rstrip().rstrip(';')
    return json.loads(raw)

C = load()
cats = C['cats']
prods = C['products']
catbyu = {c['u']: c for c in cats}

def section_of(c):
    return 'agzs' if (c or '').startswith(SECROOT['agzs']) else 'azs'

def sec_word(c):
    return 'АГЗС' if section_of(c) == 'agzs' else 'АЗС'

def cat_chain(cu):
    """список категорий от корня к листу"""
    chain = []
    cur = catbyu.get(cu)
    while cur:
        chain.append(cur)
        cur = catbyu.get(cur.get('p') or '')
    return list(reversed(chain))

# ---- группировка как в каталоге ----
def gkey(p):
    if p.get('tg'): return 't:' + str(p['tg'])
    if p.get('g'):  return 'g:' + str(p['g'])
    return None

groups = {}
for i, p in enumerate(prods):
    k = gkey(p)
    if k is not None:
        groups.setdefault(k, []).append(i)

# представитель группы — предпочитаем с фото
reps = {}
for k, members in groups.items():
    rep = members[0]
    for i in members:
        if prods[i].get('img'):
            rep = i; break
    reps[k] = rep

# список страниц (индексы представителей и одиночек) с сохранением порядка
page_indices = []
seen = set()
for i, p in enumerate(prods):
    k = gkey(p)
    if k is None:
        page_indices.append(i)
    elif k not in seen:
        seen.add(k)
        page_indices.append(reps[k])

# слаг каждой страницы (уникальный)
slug_count = {}
slug_by_page = {}
for i in page_indices:
    base = slugify(prods[i].get('n'))
    n = slug_count.get(base, 0) + 1
    slug_count[base] = n
    slug_by_page[i] = base if n == 1 else f"{base}-{n}"

# слаг для КАЖДОГО товара (члены группы -> слаг представителя)
slug_for_index = {}
for i, p in enumerate(prods):
    k = gkey(p)
    if k is None:
        slug_for_index[i] = slug_by_page.get(i)
    else:
        slug_for_index[i] = slug_by_page.get(reps[k])

# товары по категориям (для блока «похожие»)
by_cat = {}
for i in page_indices:
    by_cat.setdefault(prods[i]['c'], []).append(i)

def members_of(i):
    k = gkey(prods[i])
    return groups.get(k, [i]) if k else [i]

# ---------- шаблон страницы ----------
HEAD_LOGO = ('<a href="../index.html" class="brand">SYNDI<b>CAT</b></a>')

def render_product(i):
    p = prods[i]
    name = p.get('n') or 'Товар'
    brand = p.get('b') or ''
    c = p.get('c') or ''
    chain = cat_chain(c)
    leaf = chain[-1]['n'] if chain else 'Каталог'
    secw = sec_word(c)
    slug = slug_by_page[i]
    url = f"{BASE}/p/{slug}.html"
    img = p.get('img') or ''
    img_abs = f"{BASE}/{img}" if img else f"{BASE}/apple-touch-icon.png"
    img_rel = f"../{img}" if img else ""

    title = f"{name} — купить, цена | SYNDICAT"
    if len(title) > 70: title = f"{name[:55]}… — SYNDICAT"
    desc = f"{name}. " + (f"{brand}. " if brand else "") + \
           f"Купить для {secw}: оборудование и комплектующие SYNDICAT. Доставка по России, цена и наличие по запросу. Оригинал и аналоги."
    desc = desc[:300]
    meta_desc = desc[:165]

    # хлебные крошки (визуальные)
    crumbs = ['<a href="../index.html">Главная</a>', '<a href="../catalog.html">Каталог</a>']
    for ci in chain:
        crumbs.append(f'<a href="../catalog.html?cat={esc(ci["u"])}">{esc(ci["n"])}</a>')
    crumbs.append(f'<span>{esc(name)}</span>')
    crumbs_html = ' / '.join(crumbs)

    # фото
    if img_rel:
        photo = f'<div class="p-img"><img src="{esc(img_rel)}" alt="{esc(name)}" loading="lazy"></div>'
    else:
        photo = '<div class="p-img empty"><span class="pl">SYNDI<b>CAT</b></span><span class="pc">Фото по запросу</span></div>'

    # характеристики
    rows = ""
    for k, v in (p.get('f') or {}).items():
        if k == 'Бренд': continue
        rows += f'<tr><td>{esc(k)}</td><td>{esc(str(v))}</td></tr>'
    specs = f'<table class="p-specs"><caption>Характеристики</caption>{rows}</table>' if rows else ''

    # модификации (члены группы)
    mem = members_of(i)
    variants = ''
    if len(mem) > 1:
        items = ''
        for m in mem:
            items += f'<li>{esc(prods[m].get("n"))}</li>'
        variants = (f'<div class="p-variants"><h2>Модификации и размеры ({len(mem)})</h2>'
                    f'<ul>{items}</ul>'
                    f'<p class="muted">Подберём нужный вариант — уточните при запросе.</p></div>')

    # похожие
    sib = [x for x in by_cat.get(c, []) if x != i][:12]
    related = ''
    if sib:
        links = ''
        for s in sib:
            links += f'<li><a href="{esc(slug_by_page[s])}.html">{esc(prods[s].get("n"))}</a></li>'
        related = (f'<div class="p-related"><h2>Смотрите также в категории «{esc(leaf)}»</h2>'
                   f'<ul>{links}</ul></div>')

    # описание-текст (чтобы страница не была пустой)
    descr_block = (f'<div class="p-descr"><h2>Описание</h2><p>{esc(name)}'
                   + (f' производства {esc(brand)}' if brand else '')
                   + f' — позиция из раздела «{esc(leaf)}» для {secw}. '
                   + 'Компания SYNDICAT поставляет оборудование и комплектующие для автозаправочных '
                   + f'и газозаправочных станций по всей России. Цена и наличие «{esc(name)}» — по запросу: '
                   + 'оставьте заявку или позвоните, подберём оригинал или аналог и рассчитаем доставку.</p></div>')

    # JSON-LD
    product_ld = {"@context": "https://schema.org/", "@type": "Product", "name": name}
    if img: product_ld["image"] = [img_abs]
    product_ld["description"] = meta_desc
    if brand: product_ld["brand"] = {"@type": "Brand", "name": brand}
    if leaf: product_ld["category"] = leaf
    product_ld["url"] = url
    bc_items = [{"@type": "ListItem", "position": 1, "name": "Главная", "item": f"{BASE}/"},
                {"@type": "ListItem", "position": 2, "name": "Каталог", "item": f"{BASE}/catalog.html"}]
    pos = 3
    for ci in chain:
        bc_items.append({"@type": "ListItem", "position": pos, "name": ci['n'],
                         "item": f"{BASE}/catalog.html?cat={ci['u']}"})
        pos += 1
    bc_items.append({"@type": "ListItem", "position": pos, "name": name, "item": url})
    breadcrumb_ld = {"@context": "https://schema.org/", "@type": "BreadcrumbList", "itemListElement": bc_items}

    ld = (f'<script type="application/ld+json">{json.dumps(product_ld, ensure_ascii=False)}</script>'
          f'<script type="application/ld+json">{json.dumps(breadcrumb_ld, ensure_ascii=False)}</script>')

    mailto = f'mailto:m2@sd-kt.ru?subject={esc("Запрос цены: " + name)}'

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(meta_desc)}">
<link rel="canonical" href="{esc(url)}">
<meta name="robots" content="index, follow">
<meta property="og:type" content="product">
<meta property="og:title" content="{esc(name)}">
<meta property="og:description" content="{esc(meta_desc)}">
<meta property="og:url" content="{esc(url)}">
<meta property="og:image" content="{esc(img_abs)}">
<meta property="og:site_name" content="SYNDICAT">
<meta property="og:locale" content="ru_RU">
<link rel="icon" type="image/svg+xml" href="../favicon.svg">
<link rel="apple-touch-icon" href="../apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../assets/product.css">
{ld}
</head>
<body>
<header><div class="wrap nav">{HEAD_LOGO}
  <div class="nav-right"><a href="../catalog.html">Каталог</a><a href="tel:+73432664066" class="ph">+7 343 266-40-66</a></div>
</div></header>
<main class="wrap">
  <nav class="crumbs">{crumbs_html}</nav>
  <div class="p-top">
    <div class="p-gallery">{photo}</div>
    <div class="p-info">
      <h1>{esc(name)}</h1>
      {f'<div class="p-brand">{esc(brand)}</div>' if brand else ''}
      <div class="p-cat">Раздел: <a href="../catalog.html?cat={esc(c)}">{esc(leaf)}</a> · {secw}</div>
      {specs}
      <div class="p-actions">
        <a class="btn" href="{mailto}">Запросить цену</a>
        <a class="btn ghost" href="tel:+73432664066">Позвонить</a>
        <a class="btn ghost" href="../catalog.html?cat={esc(c)}">В каталог</a>
      </div>
      <p class="p-note">Цена и наличие — по запросу. Поставляем оригинал и аналоги. Доставка по России.</p>
    </div>
  </div>
  {variants}
  {descr_block}
  {related}
</main>
<footer class="wrap">
  <span>© 2026 SYNDICAT · sd-kt.ru · Екатеринбург, ул. Окружная, 88/2</span>
  <span class="foot-contacts"><a href="tel:+73432664066">+7 343 266-40-66</a> <a href="mailto:m2@sd-kt.ru">m2@sd-kt.ru</a> <a href="https://t.me/+79068084908" target="_blank" rel="noopener">Telegram</a> <a href="https://wa.me/79068084908" target="_blank" rel="noopener">WhatsApp</a> <a href="https://max.ru/u/f9LHodD0cOLffjdnpQtxuBmCL1xxuw8qMMhdfp6IIJ5zzUyDwaApSt6sRgQ" target="_blank" rel="noopener">Max</a></span>
</footer>
</body>
</html>"""

CSS = """:root{--studio-black:#100904;--warm-cream:#ffedd7;--cork-shadow:#40372e;--dark-cork:#382416;--burnt-sienna:#dc5000;--grey-brown:#6c5f51;--font:'Figtree',ui-sans-serif,system-ui,-apple-system,sans-serif;--maxw:1100px}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--studio-black);color:var(--warm-cream);font-family:var(--font);line-height:1.45;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
.wrap{max-width:var(--maxw);margin:0 auto;padding:0 24px}
header{position:sticky;top:0;z-index:50;border-bottom:1px solid var(--cork-shadow);background:rgba(16,9,4,.9);backdrop-filter:blur(10px)}
.nav{display:flex;align-items:center;justify-content:space-between;height:60px}
.brand{font-size:18px;font-weight:600;letter-spacing:1.5px}
.brand b{color:var(--burnt-sienna)}
.nav-right{display:flex;gap:20px;align-items:center;font-size:13px}
.nav-right a:hover{color:var(--burnt-sienna)}
.crumbs{font-size:12px;color:var(--grey-brown);margin:22px 0 18px;line-height:1.7}
.crumbs a:hover{color:var(--burnt-sienna)}
.crumbs span{color:var(--warm-cream)}
.p-top{display:grid;grid-template-columns:1fr 1fr;gap:34px;align-items:start;padding-bottom:30px}
.p-img{background:var(--warm-cream);border-radius:12px;height:420px;display:flex;align-items:center;justify-content:center;overflow:hidden}
.p-img img{width:100%;height:100%;object-fit:contain;mix-blend-mode:multiply}
.p-img.empty{background:var(--dark-cork);flex-direction:column;gap:8px;border:1px dashed var(--cork-shadow)}
.p-img .pl{font-size:22px;font-weight:600;letter-spacing:1.5px;color:var(--grey-brown)}
.p-img .pl b{color:var(--burnt-sienna)}
.p-img .pc{font-size:11px;letter-spacing:1px;color:var(--grey-brown);text-transform:uppercase}
.p-info h1{font-size:26px;font-weight:600;line-height:1.2;margin-bottom:10px}
.p-brand{font-size:14px;color:var(--grey-brown);margin-bottom:6px}
.p-cat{font-size:13px;color:var(--grey-brown);margin-bottom:18px}
.p-cat a:hover{color:var(--burnt-sienna)}
.p-specs{width:100%;border-collapse:collapse;margin-bottom:22px}
.p-specs caption{text-align:left;font-size:12px;letter-spacing:1px;color:var(--grey-brown);text-transform:uppercase;margin-bottom:8px}
.p-specs td{padding:9px 0;border-bottom:1px dashed var(--cork-shadow);font-size:13.5px;vertical-align:top}
.p-specs td:first-child{color:var(--grey-brown);width:45%;padding-right:14px}
.p-actions{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:14px}
.btn{background:var(--burnt-sienna);border:1px solid var(--burnt-sienna);color:#fff;border-radius:36px;padding:12px 24px;font-size:14px;font-weight:600;display:inline-block}
.btn.ghost{background:transparent;border-color:var(--warm-cream);color:var(--warm-cream);font-weight:500}
.btn.ghost:hover{border-color:var(--burnt-sienna);color:var(--burnt-sienna)}
.p-note{font-size:12px;color:var(--grey-brown)}
.p-variants,.p-descr,.p-related{border-top:1px dashed var(--cork-shadow);padding:26px 0}
.p-variants h2,.p-descr h2,.p-related h2{font-size:18px;font-weight:600;margin-bottom:14px}
.p-variants ul{columns:2;gap:24px;list-style:none}
.p-variants li{font-size:13.5px;padding:5px 0;border-bottom:1px dashed var(--cork-shadow);break-inside:avoid}
.p-descr p{font-size:14.5px;color:#cdbfae;max-width:780px}
.p-related ul{list-style:none;display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:8px 24px}
.p-related li{font-size:13.5px;padding:5px 0;border-bottom:1px dashed var(--cork-shadow)}
.p-related a:hover{color:var(--burnt-sienna)}
.muted{font-size:12.5px;color:var(--grey-brown);margin-top:12px}
footer{margin-top:30px;padding:30px 0;border-top:1px dashed var(--cork-shadow);font-size:12px;color:var(--grey-brown);display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap}
footer a:hover{color:var(--burnt-sienna)}
.foot-contacts a+a{margin-left:16px}
@media(max-width:760px){.wrap{padding:0 16px}.p-top{grid-template-columns:1fr;gap:20px}.p-img{height:300px}.p-variants ul{columns:1}.nav-right a:not(.ph){display:none}}
"""

def main():
    os.makedirs(os.path.join(ROOT, "p"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
    open(os.path.join(ROOT, "assets", "product.css"), "w", encoding="utf-8").write(CSS)

    for i in page_indices:
        page = render_product(i)
        open(os.path.join(ROOT, "p", slug_by_page[i] + ".html"), "w", encoding="utf-8").write(page)

    # sitemap
    urls = [f"{BASE}/", f"{BASE}/catalog.html"]
    # категории как лендинги
    for c in cats:
        urls.append(f"{BASE}/catalog.html?cat={c['u']}")
    for i in page_indices:
        urls.append(f"{BASE}/p/{slug_by_page[i]}.html")
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sm.append(f"  <url><loc>{html.escape(u, quote=True)}</loc></url>")
    sm.append("</urlset>")
    open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write("\n".join(sm))

    # переписать catalog-data.js со слагами
    for i, p in enumerate(prods):
        p['u'] = slug_for_index[i]
    js = "window.CATALOG=" + json.dumps(C, ensure_ascii=False, separators=(',', ':')) + ";"
    open(DATA, "w", encoding="utf-8").write(js)

    print(f"страниц товаров: {len(page_indices)}")
    print(f"ссылок в sitemap: {len(urls)}")
    print(f"слаги добавлены в catalog-data.js")

if __name__ == "__main__":
    main()
