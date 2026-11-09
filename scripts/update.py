"""Tägliche Aktualisierung von Fair Price Marrakech.

1. Wechselkurse (MAD pro 1 EUR/USD/GBP/CHF/CAD) von open.er-api.com
2. Apotheken mit Nachtdienst in Marrakesch von annuaire-gratuit.ma
3. Holt die 7-Tage-Wetterprognose (Open-Meteo, frei, ohne Schlüssel)
4. Schreibt alles in docs/index.html (Blöcke /*RATES*/, /*PHARM*/, /*WX*/)

Sicherheitsregel: Liefert eine Quelle nichts Brauchbares, bleiben die alten Daten stehen.
Die App blendet Apotheken-Daten, die älter als 36 Stunden sind, selbst aus.
"""
import datetime as dt
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs" / "index.html"
TZ = dt.timezone(dt.timedelta(hours=1))  # Marokko (UTC+1); während Ramadan UTC+0 – für das Datum unerheblich
HEADERS = {"User-Agent": "FairPriceMarrakech-Updater/1.0 (+GitHub Actions)", "Accept-Language": "fr,en;q=0.8"}

RATES_URL = "https://open.er-api.com/v6/latest/EUR"
RANGES = {"EUR": (9.5, 12.5), "USD": (8.5, 11.5), "GBP": (11, 15.5), "CHF": (10, 14), "CAD": (6, 8.5)}

WX_URL = ("https://api.open-meteo.com/v1/forecast?latitude=31.63&longitude=-8.01"
          "&daily=weather_code,temperature_2m_max,temperature_2m_min,uv_index_max,precipitation_probability_max"
          "&timezone=Africa%2FCasablanca&forecast_days=7")
PHARM_URL = "https://www.annuaire-gratuit.ma/pharmacie-garde-marrakech/garde-nuit.html"
PHONE_RE = re.compile(r"(?:\+212[\s.\-]?|0)[5-7](?:[\s.\-]?\d){8}")
MAX_DETAIL_PAGES = 30


def log(*a):
    print(*a, flush=True)


# ---------------------------------------------------------------- Wechselkurse
def fetch_rates(old):
    r = requests.get(RATES_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    j = r.json()
    if j.get("result") != "success":
        raise RuntimeError(f"Kurs-API: {j.get('result')}")
    eur = j["rates"]
    mad_per_eur = eur["MAD"]
    new = dict(old.get("MAD", {}))
    for c, (lo, hi) in RANGES.items():
        v = mad_per_eur if c == "EUR" else mad_per_eur / eur[c]
        v = round(v, 2)
        if lo <= v <= hi:
            new[c] = v
        else:
            log(f"Kurs {c}={v} unplausibel – alter Wert bleibt")
    date = dt.datetime.fromtimestamp(j["time_last_update_unix"], dt.timezone.utc).date().isoformat()
    return {"date": date, "MAD": new}


# ---------------------------------------------------------------- Apotheken
def norm_phone(s):
    d = re.sub(r"\D", "", s)
    if d.startswith("212"):
        d = "0" + d[3:]
    if len(d) != 10:
        return ""
    return f"{d[:4]} {d[4:6]} {d[6:8]} {d[8:]}"


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip(" -–|·,")


def find_cards(soup):
    """Sucht Karten: kleinster Container um einen Namen „Pharmacie …“."""
    cards, seen = [], set()
    for tag in soup.find_all(["a", "h2", "h3", "h4", "strong", "b", "span", "div"]):
        txt = clean(tag.get_text(" "))
        if not re.match(r"^Pharmacie\s+\S", txt) or len(txt) > 60:
            continue
        # nur das innerste Element mit dem Namen nehmen (nicht den umgebenden Block)
        if any(re.match(r"^Pharmacie\s+\S", clean(ch.get_text(" ")))
               for ch in tag.find_all(["a", "h2", "h3", "h4", "strong", "b", "span", "div"])):
            continue
        name = txt
        box = tag
        for _ in range(5):  # nach oben bis zu einem Block mit Adresse
            if box.parent is None:
                break
            box = box.parent
            bt = clean(box.get_text(" "))
            if len(bt) > len(name) + 15:
                break
        bt = clean(box.get_text(" "))
        if len(bt) > 600 or bt.count("Pharmacie ") > 2:  # Container zu groß -> nur Name
            bt = name
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        link = tag if tag.name == "a" else tag.find("a") or (tag.find_parent("a"))
        href = urljoin(PHARM_URL, link["href"]) if link is not None and link.get("href") else ""
        cards.append({"name": name, "text": bt, "box": box, "href": href})
    return cards


def phone_from(node_or_html):
    soup = node_or_html if hasattr(node_or_html, "find_all") else BeautifulSoup(node_or_html, "html.parser")
    for a in soup.find_all("a", href=True):
        if a["href"].startswith("tel:"):
            p = norm_phone(a["href"][4:])
            if p:
                return p
    for attr in ("data-phone", "data-tel", "data-number"):
        el = soup.find(attrs={attr: True})
        if el:
            p = norm_phone(el[attr])
            if p:
                return p
    m = PHONE_RE.search(soup.get_text(" "))
    return norm_phone(m.group(0)) if m else ""


def address_from(card):
    t = card["text"]
    t = t.replace(card["name"], " ")
    t = PHONE_RE.sub(" ", t)
    t = re.sub(r"\d{2}[\s.]?\d{2}[\s.]?\d{2}\s*[•\*x]+.*", " ", t)  # maskierte Nummern
    t = re.sub(r"(?i)(itinéraire|appeler|voir le numéro|afficher le numéro|garde (de )?(nuit|jour|24h)|ouvert( en ce moment)?|fermé)", " ", t)
    return clean(t)[:140]


def fetch_pharmacies():
    r = requests.get(PHARM_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    cards = find_cards(soup)
    items = []
    details = 0
    for c in cards:
        phone = phone_from(c["box"])
        if not phone and c["href"] and details < MAX_DETAIL_PAGES:
            details += 1
            try:
                time.sleep(1)
                d = requests.get(c["href"], headers=HEADERS, timeout=20)
                if d.ok:
                    phone = phone_from(d.text)
            except requests.RequestException as e:
                log("Detailseite nicht erreichbar:", c["href"], e)
        items.append({"n": c["name"], "a": address_from(c), "q": "", "t": phone})
    return items


# ---------------------------------------------------------------- Seite schreiben
def fetch_weather():
    r = requests.get(WX_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    d = r.json()["daily"]
    days = [[d["time"][i], d["weather_code"][i], round(d["temperature_2m_max"][i]), round(d["temperature_2m_min"][i]),
             round(d["uv_index_max"][i] or 0), d["precipitation_probability_max"][i] or 0] for i in range(len(d["time"]))]
    if len(days) < 3:
        raise RuntimeError("zu wenige Tage")
    return {"days": days}


def read_block(html, name):
    m = re.search(rf"/\*{name}\*/const {name}=(.*?);/\*END_{name}\*/", html, re.S)
    return json.loads(m.group(1)) if m else {}


def write_block(html, name, data):
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    new, n = re.subn(rf"/\*{name}\*/const {name}=.*?;/\*END_{name}\*/",
                     lambda _: f"/*{name}*/const {name}={payload};/*END_{name}*/", html, flags=re.S)
    if n != 1:
        raise RuntimeError(f"Block {name} nicht gefunden")
    return new


def main():
    html = PAGE.read_text(encoding="utf-8")
    changed = False
    try:
        rates = fetch_rates(read_block(html, "RATES"))
        html = write_block(html, "RATES", rates); changed = True
        log("Kurse:", rates)
    except Exception as e:  # noqa: BLE001
        log("Kurse nicht aktualisiert:", e)
    try:
        wx = fetch_weather()
        html = write_block(html, "WX", wx); changed = True
        log("Wetter:", wx["days"][0])
    except Exception as e:  # noqa: BLE001
        log("Wetter nicht aktualisiert:", e)
    try:
        items = fetch_pharmacies()
        if len(items) >= 3:
            today = dt.datetime.now(TZ).date().isoformat()
            html = write_block(html, "PHARM", {"date": today, "type": "nuit", "source": "annuaire-gratuit.ma", "items": items})
            changed = True
            log(f"Apotheken: {len(items)} (mit Telefon: {sum(1 for i in items if i['t'])})")
        else:
            log(f"Apotheken: nur {len(items)} gefunden – alte Daten bleiben (App blendet sie nach 36 h aus)")
    except Exception as e:  # noqa: BLE001
        log("Apotheken nicht aktualisiert:", e)
    if changed:
        PAGE.write_text(html, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
