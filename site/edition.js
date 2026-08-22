/* Editieschakelaar: het zwevende vlakje en het verwisselen van het vel.

   1. Het witte vlakje achter het huidige editienummer is één los element dat
      naar het gehoverde cijfer schuift (CSS doet de beweging via een
      transition op --x/--w; zie .edition-switch-marker in style.css).
   2. Een andere editie kiezen vervangt de inhoud van .expo-row rechtstreeks,
      zonder de pagina opnieuw te laden: het oude vel kantelt linksom weg, de
      nieuwe inhoud komt ervoor in de plaats en kantelt van rechts binnen. De
      HTML daarvoor staat kant-en-klaar in edities.js (window.DD_EDITIES) —
      dezelfde opmaak als de statische editiepagina's, want build.py maakt ze
      allebei met expo_row_inner().

   Zonder JavaScript, zonder edities.js, of als history.pushState niet mag
   (dat gooit over file:// een SecurityError), gebeurt gewoon een normale
   navigatie naar editie-N.html. */
(function () {
  "use strict";

  var UIT_DUUR = 600;   // vangnet: iets boven de 0,34s van sheet-out

  /* ---------------- het zwevende vlakje ---------------- */

  // Wordt na elke wissel opnieuw gedraaid: de schakelaar zit ín de vervangen
  // inhoud, dus het oude vlakje en zijn listeners zijn dan verdwenen.
  function initMarker() {
    var nav = document.querySelector(".edition-switch");
    if (!nav) return;
    var lijst = nav.querySelector("ul");
    var huidige = nav.querySelector(".is-current");
    if (!lijst || !huidige) return;

    // Een <li> (en niet een <span>) houdt de lijst geldig; absoluut
    // gepositioneerd telt hij niet mee in de flex-layout.
    var marker = document.createElement("li");
    marker.className = "edition-switch-marker";
    marker.setAttribute("aria-hidden", "true");
    lijst.appendChild(marker);
    nav.classList.add("has-marker");

    var items = nav.querySelectorAll("a, .is-current");

    // De li's zijn zelf position: relative (voor de z-index boven het vlakje),
    // dus offsetLeft van een cijfer telt vanaf zijn eigen li. Optellen tot aan
    // de lijst geeft de echte x. Bewust via offsetLeft en niet via
    // getBoundingClientRect: het vel kantelt bij het laden (sheet-in), en
    // gemeten rects zijn dan vervormd — offsets zijn dat niet.
    function xInLijst(el) {
      var x = 0;
      while (el && el !== lijst) {
        x += el.offsetLeft;
        el = el.offsetParent;
      }
      return x;
    }

    function zetOp(el) {
      marker.style.setProperty("--x", xInLijst(el) + "px");
      marker.style.setProperty("--w", el.offsetWidth + "px");
      for (var i = 0; i < items.length; i++) {
        items[i].classList.toggle("is-marked", items[i] === el);
      }
    }

    zetOp(huidige);
    // Pas in het volgende frame mag hij gaan meebewegen, anders schuift het
    // vlakje bij het laden zichtbaar vanaf links naar zijn plek.
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { marker.classList.add("is-ready"); });
    });

    for (var i = 0; i < items.length; i++) {
      (function (el) {
        el.addEventListener("mouseenter", function () { zetOp(el); });
        // Ook voor wie met de tab-toets door de nummers loopt.
        el.addEventListener("focus", function () { zetOp(el); });
      })(items[i]);
    }

    lijst.addEventListener("mouseleave", function () { zetOp(huidige); });
    nav.addEventListener("focusout", function (e) {
      if (!nav.contains(e.relatedTarget)) zetOp(huidige);
    });
    window.addEventListener("resize", function () {
      if (!document.contains(marker)) return;   // na een wissel niet meer nodig
      zetOp(nav.querySelector(".is-marked") || huidige);
    });
  }

  /* ---------------- van editie wisselen ---------------- */

  function nummerUitUrl(url) {
    var m = /editie-(\d+)\.html/.exec(url);
    // De voorpagina toont de nieuwste editie.
    return m ? m[1] : String(window.DD_EDITIE_LAATSTE || "");
  }

  function isHome(pad) {
    return !/editie-\d+\.html/.test(pad);
  }

  function toon(nummer) {
    var data = window.DD_EDITIES && window.DD_EDITIES[nummer];
    var rij = document.querySelector(".expo-row");
    if (!data || !rij) return false;

    // De klasse moet weg vóór het invoegen, anders erft het nieuwe vel
    // meteen sheet-out in plaats van sheet-in.
    document.body.classList.remove("sheet-leaving");
    rij.setAttribute("style", data.vars);
    rij.innerHTML = data.html;
    // Op de voorpagina staat dezelfde editie, maar onder de eigen titel.
    document.title = (isHome(location.pathname) && window.DD_TITEL_HOME)
      ? window.DD_TITEL_HOME : data.title;
    window.scrollTo(0, 0);

    initMarker();
    document.dispatchEvent(new CustomEvent("dd:swap"));
    return true;
  }

  function wissel(doelUrl) {
    var nummer = nummerUitUrl(doelUrl);
    if (!window.DD_EDITIES || !window.DD_EDITIES[nummer]) return false;

    // Over file:// heeft elk bestand een eigen "opaque" origin, ook binnen
    // dezelfde map — pushState naar een ander bestand gooit dan altijd een
    // SecurityError (vandaar ook de <script>-omweg voor de zoekindex). De
    // wissel zelf hoeft daar niet op te wachten: lukt het niet, dan blijft de
    // adresbalk simpelweg op de huidige pagina staan terwijl de inhoud (en de
    // animatie) gewoon verandert.
    try {
      history.pushState({ editie: nummer }, "", doelUrl);
    } catch (e) { /* geen probleem, zie hierboven */ }

    var vel = document.querySelector("main.expo");
    if (!vel) { toon(nummer); return true; }

    document.body.classList.add("sheet-leaving");

    var gedaan = false;
    function daarna() {
      if (gedaan) return;
      gedaan = true;
      toon(nummer);
    }
    vel.addEventListener("animationend", function (e) {
      if (e.target === vel) daarna();
    });
    setTimeout(daarna, UIT_DUUR);
    return true;
  }

  // Gedelegeerd, want de schakelaar zelf wordt bij elke wissel vervangen.
  document.addEventListener("click", function (e) {
    var a = e.target.closest ? e.target.closest(".edition-switch a") : null;
    if (!a) return;
    // Nieuw tabblad, middelklik en dergelijke met rust laten.
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;

    if (wissel(a.getAttribute("href"))) e.preventDefault();
    // Lukt het wisselen niet, dan volgt gewoon de link.
  });

  // Terug- en vooruitknop: dezelfde wissel, maar zonder nieuwe geschiedenis.
  window.addEventListener("popstate", function () {
    toon(nummerUitUrl(location.pathname));
  });

  initMarker();
})();
