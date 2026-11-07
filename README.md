# Fair Price Marrakech

Faire Preise für Touristen in Marrakesch – mit SOS-Nummern, Reise-Infos,
Wechselkursen und den Apotheken mit Nachtdienst. Kurse und Apotheken
werden **jeden Tag automatisch** aktualisiert.

## Einrichten (einmalig, ca. 10 Minuten)

1. **Konto anlegen:** Auf <https://github.com> kostenlos registrieren.
2. **Neues Repository:** Oben rechts **+ → New repository**.
   Name z. B. `fair-price-marrakech`, Sichtbarkeit **Public**, dann **Create repository**.
3. **Dateien hochladen:** Im neuen Repository auf **uploading an existing file** klicken
   und den **gesamten Inhalt** dieses Ordners hineinziehen (die Ordner `docs`,
   `scripts` und `.github` sowie diese Datei). Unten **Commit changes**.
   > Hinweis: Der Ordner `.github` ist auf manchen Computern versteckt.
   > Am Handy oder wenn er fehlt: im Repository **Add file → Create new file**,
   > als Namen `.github/workflows/update.yml` eintippen und den Inhalt der Datei hineinkopieren.
4. **Webseite einschalten:** **Settings → Pages** → bei *Source* „Deploy from a branch“,
   Branch `main`, Ordner **`/docs`** → **Save**.
   Nach 1–2 Minuten steht oben die Adresse, z. B.
   `https://IHR-NAME.github.io/fair-price-marrakech/` – das ist der Link für die Touristen.
5. **Automatik erlauben:** **Settings → Actions → General** → ganz unten bei
   *Workflow permissions* „Read and write permissions“ wählen → **Save**.
6. **Erster Test:** Reiter **Actions** → „Taegliche Aktualisierung“ → **Run workflow**.
   Nach etwa einer Minute erscheint ein grüner Haken. Im Protokoll steht, wie viele
   Apotheken gefunden wurden und welche Kurse gesetzt wurden.

Ab dann läuft alles von selbst, jeden Tag um 18:23 Uhr (Marokko).

## Was passiert, wenn eine Quelle ausfällt?

- **Kurse:** Unplausible Werte werden nicht übernommen, der alte Kurs bleibt stehen.
  Neben dem Kurs steht immer sein Datum.
- **Apotheken:** Findet das Programm weniger als 3 Apotheken, bleiben die alten Daten
  stehen. Die App **blendet Apotheken-Listen, die älter als 36 Stunden sind, automatisch aus**
  und zeigt stattdessen den Hinweis auf den Aushang an jeder geschlossenen Apotheke.
  So wird niemand zu einer Apotheke geschickt, die gar keinen Dienst hat.
- Wenn die Quellseite ihren Aufbau ändert, kann das Auslesen aufhören zu funktionieren.
  Das sieht man im Reiter **Actions** im Protokoll („Apotheken: nur 0 gefunden“).
  Dann muss `scripts/update.py` angepasst werden.

## Quellen

- Wechselkurse: open.er-api.com (kostenlos, ohne Anmeldung)
- Nachtapotheken: annuaire-gratuit.ma – bitte vor dem öffentlichen Start die
  Nutzungsbedingungen der Seite prüfen bzw. um Erlaubnis bitten.
- Preise: eigene Erhebung und Referenzlisten (siehe Hinweise in der App)

## Inhalt dieses Ordners

| Datei | Zweck |
|---|---|
| `docs/index.html` | Die App (eine einzige Datei, inklusive Bilder) |
| `scripts/update.py` | Holt Kurse und Apotheken und schreibt sie in die App |
| `.github/workflows/update.yml` | Startet das Programm täglich automatisch |
