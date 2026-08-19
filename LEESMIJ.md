# De Dissident — website

De site wordt **gegenereerd** uit één inhoudsbestand en de magazine-PDF's.
Bewerk nooit iets in `site/` — die map wordt bij elke build weggegooid.

## Bouwen

```bash
python3 build.py
```

Wil je alleen aan de vormgeving werken, dan kan het uitlezen van de PDF's overgeslagen worden:

```bash
python3 build.py --no-text
```

Open daarna `site/index.html`.

## Wat waar staat

| Map / bestand | Wat het is |
|---|---|
| `content/site.json` | **De enige plek waar je content aanpast.** Edities, artikelen, auteurs, rubrieken, paginanummers. |
| `content/cache/` | Uitgelezen tekst per artikel. Weggooien = opnieuw uitlezen uit de PDF's. |
| `static/style.css` | De vormgeving. |
| `static/search.js` | Zoeken en het rubrieken-menu. |
| `lib/reflow.py` | Herstelt leesbare alinea's uit PDF-tekst (kolommen, afbreekstreepjes, kopregels). |
| `lib/iwa.py` | Leest Apple Pages-bestanden. |
| `site/` | Het resultaat. Gegenereerd — niet bewerken. |

## Een artikel toevoegen of aanpassen

Alles gebeurt in `content/site.json`. Eén artikel ziet er zo uit:

```json
{
  "page": 42,
  "end": 45,
  "title": "Anti-Industrieel Extremisme",
  "subtitle": "Over de ideeën van Theodor Kaczynski",
  "category": "Essay",
  "author": "De Dissident",
  "image": "industrieel extremisme"
}
```

- `page` / `end` — paginabereik in de gedrukte editie. Laat je `end` weg, dan loopt het
  artikel tot de pagina vóór het volgende artikel.
- `category` — vult automatisch het rubrieken-menu en het filter op de archiefpagina.
- `image` — voor editie 6 de mapnaam in `DD blad/6/Links/`; met `site:bestand.jpg`
  pak je een foto uit `DD site/sources/`. Laat je het leeg, dan krijgt de kaart een
  gekleurd vlak met het paginacijfer.
- `note` — een redactienotitie die bovenaan het artikel verschijnt.

Daarna `python3 build.py` draaien.

## Hoe de site technisch in elkaar zit

- **Werkt zonder server.** De zoekindex wordt als script geladen, niet met `fetch()`;
  dat laatste blokkeren browsers op `file://`. Je kunt `site/index.html` dus gewoon
  vanuit Finder openen en zoeken werkt.
- **Zoekindex laadt pas bij gebruik.** Een pagina begint op ~30 KB; de index van
  112 KB komt er pas bij als je zoekt of het rubriekenmenu opent.
- **Twee beeldformaten per artikel** (800 en 1600 px, JPEG). De browser kiest via
  `srcset`; op een telefoon wordt de kleine geladen.
- **Toegankelijkheid**: één `h1` per pagina met een kloppende koppenstructuur,
  skip-link naar de inhoud, zichtbare focusrand, `aria-live`-melding met het aantal
  zoekresultaten, en tekstkleuren die 4,5:1 contrast halen.
- **404-pagina** in `site/404.html`, en een `noscript`-melding voor bezoekers
  zonder JavaScript (het archief werkt wel zonder).

## Wat nog aandacht vraagt

- **De artikelteksten zijn machinaal uit de PDF's gehaald en zijn niet nagelezen.**
  Waar een cursieve regel over de kolomgoot loopt kan een letter ontbreken.
- **Editie 7** heeft nog geen PDF. Alleen het interview met Frederik Jansen heeft tekst,
  gelezen uit `DD blad/7/Interview Freek.pages`. De rest wacht op de definitieve PDF.
- **Editie 3** heeft een opmaak waarin twee kolommen soms door elkaar lopen; die
  artikelen hebben een correctieslag nodig.
- **Pagina's die vooral beeld zijn** leveren geen tekst op en tonen een nette melding.
- **Editie 4** staat met één artikel in de index. Die inhoudsopgave heeft een afwijkende
  opmaak die niet automatisch uit te lezen was; de rest moet nog handmatig in
  `content/site.json`.
- In de inhoudsopgave van de proefversie van editie 7 stond bij *De Noord-Zuidlijn* een
  racistische werktitel. Die is bewust niet overgenomen — de ondertitel is
  "Op de noodstroom in Zuid-Afrika", zoals Bob hem heeft opgegeven.
- Alleen editie 6 heeft beeld per artikel; voor de andere edities staan de
  originelen nog niet als losse bestanden klaar.
