# BAUHAUS prisbevakning – Fibrotech SPC

Detta projekt bevakar **två väggpaneler** hos BAUHAUS och skickar Telegram-notis
när någon av dem kostar **mindre än 799 kr**. Varje produkt bevakas separat.
Det använder samma GitHub Actions/Telegram-princip som Mio-prisbevakningen.

| Produkt | BAUHAUS-artikelnummer | Pris vid uppsättning | Varningsgräns |
|---|---|---:|---:|
| Fibrotech SPC Vit marmor (1000 × 2600 mm) | 1676868 | 799 kr | < 799 kr |
| Fibrotech SPC Grå marmor (1000 × 2600 mm) | 1676867 | 799 kr | < 799 kr |

## 1. Skapa GitHub-repo

Skapa ett **privat** repository, exempelvis `bauhaus-prisbevakning`.
Lägg in samtliga filer från detta paket. Behåll mappen
`.github/workflows/` exakt som den är.

Du kan också lägga in filerna i ett befintligt repo, men säkerställ att
filnamnen inte krockar med din tidigare Mio-bevakning.

## 2. Lägg in Telegram Secrets

Gå till GitHub-repot → **Settings** → **Secrets and variables** → **Actions**
→ **New repository secret**. Skapa:

- `TELEGRAM_BOT_TOKEN` = token till din befintliga Telegram-bot
- `TELEGRAM_CHAT_ID` = samma chat-id som i Mio-bevakningen

Du kan återanvända **värdena**, men nya repository secrets behövs i ett nytt repo.
Lägg aldrig in token eller chat-id direkt i koden.

## 3. Testa

Öppna fliken **Actions** → **BAUHAUS prisbevakning** → **Run workflow**.
Titta i körningens loggar efter priserna. Vid **799 kr skickas ingen varning**.

Om du vill testa Telegram-notisen kan du tillfälligt ändra
`"prisgrans": Decimal("799")` till `Decimal("1000")` för en produkt,
köra manuellt och sedan sätta tillbaka `799`. Vid test med en ny gräns
kommer en notis att skickas om sidan kan läsas.

## 4. Automatisk bevakning

Schemat kör var sjätte timme, UTC (klockan 00:17, 06:17, 12:17 och 18:17 UTC).
GitHub kan ibland fördröja schemalagda körningar.

Status sparas i `varning_skickad.json` så att boten inte skickar samma
varning gång på gång. Om priset stiger tillbaka till minst 799 kr kan en
ny prissänkning ge en ny varning.

**Viktigt:** BAUHAUS kan ändra hemsidans HTML eller blockera automatiska
förfrågningar. HTML-avläsningen är därför byggd med flera alternativ,
men första verkliga körningen måste kontrolleras i Actions-loggen.

## Ändra prisgränser

I `price_monitor.py` finns `PRODUKTER`. Ändra `Decimal("799")` under
`"prisgrans"` individuellt för vit/grå panel.

## Viktigt om erbjudanden

Bevakningen tittar efter listat produktpris på produktsidan, inte
rabatt som först dras i varukorgen vid ett visst totalbelopp.
