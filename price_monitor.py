"""Bevaka två BAUHAUS-väggpaneler och skicka Telegram-varning vid prissänkning.

För att byta prisgräns: ändra "prisgrans" för respektive produkt.
Telegram-autentisering läses från GitHub Actions Secrets.
"""

import json
import os
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

import requests
from bs4 import BeautifulSoup


PRODUKTER = {
    "vit_marmor": {
        "namn": "Fibrotech SPC – Vit marmor",
        "url": "https://www.bauhaus.se/vaggpanel-fibrotech-spc-vit-marmor-1000x2600mm-1063413",
        "prisgrans": Decimal("799"),
    },
    "gra_marmor": {
        "namn": "Fibrotech SPC – Grå marmor",
        "url": "https://www.bauhaus.se/vaggpanel-fibrotech-spc-gra-marmor-2600x1000mm-1063411",
        "prisgrans": Decimal("799"),
    },
}

STATUSFIL = Path(__file__).with_name("varning_skickad.json")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def till_pris(varde):
    """Tolka t.ex. 799,00 kr, 799.00, 1 299,00 och 1.299,00."""
    if isinstance(varde, (int, float, Decimal)):
        pris = Decimal(str(varde))
    elif isinstance(varde, str):
        siffror = re.sub(r"[^\d,.]", "", varde.replace("\u00a0", ""))
        if not siffror:
            return None
        if "," in siffror and "." in siffror:
            # Den sista separatorn är normalt decimaltecknet.
            siffror = (siffror.replace(".", "").replace(",", ".")
                       if siffror.rfind(",") > siffror.rfind(".")
                       else siffror.replace(",", ""))
        elif "," in siffror:
            siffror = siffror.replace(",", ".")
        elif siffror.count(".") == 1 and len(siffror.split(".")[-1]) == 3:
            siffror = siffror.replace(".", "")
        try:
            pris = Decimal(siffror)
        except InvalidOperation:
            return None
    else:
        return None
    return pris if pris > 0 else None


def jsonld_produkt_priser(nod):
    """Hämta pris ur strukturerad Product-data (även @graph/nästlade listor)."""
    if isinstance(nod, list):
        for delnod in nod:
            yield from jsonld_produkt_priser(delnod)
    elif isinstance(nod, dict):
        typ = nod.get("@type", "")
        typer = typ if isinstance(typ, list) else [typ]
        if any(str(t).lower().endswith("product") for t in typer):
            offers = nod.get("offers", [])
            offers = offers if isinstance(offers, list) else [offers]
            for offer in offers:
                if isinstance(offer, dict):
                    for f in (offer.get("price"), offer.get("lowPrice")):
                        pris = till_pris(f)
                        if pris is not None:
                            yield pris
                    spec = offer.get("priceSpecification")
                    if isinstance(spec, dict):
                        pris = till_pris(spec.get("price"))
                        if pris is not None:
                            yield pris
        for v in nod.values():
            if isinstance(v, (dict, list)):
                yield from jsonld_produkt_priser(v)


def hamta_pris_fran_html(html):
    """Välj ordinarie produktpris; undvik kampanjtexter och rekommendationer."""
    soup = BeautifulSoup(html, "html.parser")

    # 1. Produktens strukturerade data (vanligt för e-handel och Google).
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or script.get_text())
        except (ValueError, TypeError):
            continue
        for pris in jsonld_produkt_priser(data):
            return pris

    # 2. Strukturerade pris-taggar i produktsidan.
    for selector, attribut in (
        ('meta[property="product:price:amount"]', "content"),
        ('meta[itemprop="price"]', "content"),
        ('[itemprop="offers"] [itemprop="price"]', "content"),
        ('[data-price-type="finalPrice"] [data-price-amount]', "data-price-amount"),
        ('.product-info-main [data-price-amount]', "data-price-amount"),
    ):
        for element in soup.select(selector):
            pris = till_pris(element.get(attribut))
            if pris is not None:
                return pris

    # 3. Som sista försök: priset i huvudproduktens prisruta.
    for selector in (
        '.product-info-main [data-price-type="finalPrice"] .price',
        '.product-info-main .price-box .price',
        'main .product-info-price .price',
    ):
        for element in soup.select(selector):
            pris = till_pris(element.get_text(" ", strip=True))
            if pris is not None:
                return pris

    raise ValueError("Kunde inte läsa produktpriset från BAUHAUS-sidan (sidans HTML kan ha ändrats).")


def hamta_pris(url):
    svar = requests.get(url, headers=HEADERS, timeout=25)
    svar.raise_for_status()
    return hamta_pris_fran_html(svar.text)


def telegram_meddelande(text):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    svar = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"},
        timeout=20,
    )
    svar.raise_for_status()
    resultat = svar.json()
    if not resultat.get("ok"):
        raise RuntimeError(f"Telegram returnerade fel: {resultat.get('description')}")


def las_status():
    if not STATUSFIL.exists():
        return {}
    return json.loads(STATUSFIL.read_text(encoding="utf-8"))


def spara_status(status):
    STATUSFIL.write_text(
        json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def kor():
    # Kontrollera Secrets före första nätverksanropet.
    if not os.getenv("TELEGRAM_BOT_TOKEN") or not os.getenv("TELEGRAM_CHAT_ID"):
        raise RuntimeError("TELEGRAM_BOT_TOKEN eller TELEGRAM_CHAT_ID saknas i GitHub Secrets.")

    status = las_status()
    fel = []
    for produkt_id, produkt in PRODUKTER.items():
        try:
            pris = hamta_pris(produkt["url"])
            gransen = produkt["prisgrans"]
            aktuell = status.get(produkt_id, {})
            tidigare_varning = aktuell.get("varning_skickad", False)
            print(f"{produkt['namn']}: {pris} kr (varningsgräns: under {gransen} kr)")

            if pris < gransen and not tidigare_varning:
                telegram_meddelande(
                    "🔔 PRISSÄNKNING HOS BAUHAUS!\n\n"
                    f"{produkt['namn']}\n"
                    f"Nytt pris: {pris} kr\n"
                    f"Tidigare riktpris: {gransen} kr\n"
                    f"Du sparar: {gransen - pris} kr per panel\n\n"
                    f"{produkt['url']}"
                )
                print("Telegram-varning skickad.")
                varning_skickad = True
            elif pris >= gransen:
                # Nollställ varningen om priset återgår till normalnivån.
                varning_skickad = False
            else:
                print("Redan varnat om pris under gränsen – ingen dubblett.")
                varning_skickad = True

            status[produkt_id] = {
                "senaste_pris": str(pris),
                "varning_skickad": varning_skickad,
            }
        except Exception as exc:
            print(f"FEL – {produkt['namn']}: {exc}", file=sys.stderr)
            fel.append(produkt_id)

    spara_status(status)
    if fel:
        print(f"Kunde inte kontrollera: {', '.join(fel)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    kor()
