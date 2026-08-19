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
| `content/site.json` | **De enige plek waar je content aanpast.** Edities, artikelen, auteurs, rubrieken. |
| `content/cache/` | Uitgelezen tekst per artikel. Weggooien = opnieuw uitlezen uit de PDF's. |
| `static/style.css` | De vormgeving. |
| `static/search.js` | Zoeken en het rubrieken-menu. |
| `lib/reflow.py` | Herstelt leesbare alinea's uit PDF-tekst (kolommen, afbreekstreepjes, kopregels). |
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

- `page` / `end` — paginabereik in de gedrukte editie. Dit is **alleen een bouwgegeven**:
  het bepaalt welke PDF-pagina's bij het artikel horen en in welke volgorde de artikelen
  staan. Op de site zelf komen geen paginanummers voor. Laat je `end` weg, dan loopt het
  artikel tot de pagina vóór het volgende. Laat je `page` leeg (`null`), dan krijgt het
  artikel geen tekst en komt het achteraan.
- `category` — vult automatisch het rubrieken-menu en het filter op de archiefpagina.
- `image` — de mapnaam in de bronmap van die editie (zie `ART_FOLDERS` in `build.py`):
  `DD blad/6/Links/` voor editie 6, `DD blad/7/bronnen/` voor editie 7. Uit de map wordt
  het grootste beeld gekozen. Laat je het leeg, dan krijgt de kaart een gekleurd vlak.
- `note` — een redactienotitie die bovenaan het artikel verschijnt.

Een editie waarvan de proefdruk twee bladpagina's op één PDF-pagina zet (een spread)
krijgt `"pages_per_sheet": 2`; de build rekent de paginanummers dan zelf om.

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
- **Editie 7** komt uit de proefdruk (`DD blad/7/proefdruk/binnenwerk.pdf`), die zeven
  artikelen bevat. Vier titels uit de eerdere inhoudsopgave staan er niet in en hebben
  daarom geen tekst en geen paginanummer; ze staan onderaan de editie met een notitie.
  Die inhoudsopgave is achterhaald — de proefdruk wijkt er in paginering én in inhoud
  van af.
- **Pagina's die vooral beeld zijn** leveren geen tekst op en tonen een nette melding.
- **Editie 4** staat met één artikel in de index. Die inhoudsopgave heeft een afwijkende
  opmaak die niet automatisch uit te lezen was; de rest moet nog handmatig in
  `content/site.json`.
- In de inhoudsopgave van de proefversie van editie 7 stond bij *De Noord-Zuidlijn* een
  racistische werktitel. Die is bewust niet overgenomen — de ondertitel is
  "Op de noodstroom in Zuid-Afrika", zoals Bob hem heeft opgegeven.
- **Editie 6 en 7 hebben beeld per artikel**; voor editie 1 t/m 5 staan de originelen
  nog niet als losse bestanden klaar, dus die kaarten tonen een gekleurd vlak.
- Sommige alinea's beginnen met een kopregel die de PDF meelevert ("Een Interview Met
  Frederik Jansen …"). Dat is geen fout in de tekst, maar wel iets om bij het nalezen
  weg te halen.
