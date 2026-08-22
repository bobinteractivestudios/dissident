/* Editieschakelaar: het zwevende vlakje en de vel-wissel.

   1. Het witte vlakje achter het huidige editienummer is één los element dat
      naar het gehoverde cijfer schuift (CSS doet de beweging via een
      transition op --x/--w; zie .edition-switch-marker in style.css).
   2. Bij het kiezen van een andere editie kantelt het vel eerst linksom weg,
      en pas daarna volgt de navigatie — de nieuwe pagina kantelt vanzelf van
      rechts binnen, want main.expo draagt sheet-in bij elke lading.

   Zonder JavaScript gebeurt geen van beide en blijft de schakelaar een gewone
   lijst links: .is-current houdt dan zijn eigen achtergrond (style.css). */
(function () {
  "use strict";

  var nav = document.querySelector(".edition-switch");
  if (!nav) return;

  var lijst = nav.querySelector("ul");
  var huidige = nav.querySelector(".is-current");
  if (!lijst || !huidige) return;

  /* ---------------- het zwevende vlakje ---------------- */

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

  // Bij een andere vensterbreedte kloppen de gemeten posities niet meer.
  window.addEventListener("resize", function () {
    var actief = nav.querySelector(".is-marked") || huidige;
    zetOp(actief);
  });

  /* ---------------- het vel verwisselen ---------------- */

  nav.addEventListener("click", function (e) {
    var a = e.target.closest ? e.target.closest("a") : null;
    if (!a || !nav.contains(a)) return;
    // Nieuw tabblad, middelklik en dergelijke met rust laten.
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;

    e.preventDefault();
    var doel = a.href;
    var vel = document.querySelector("main.expo");
    if (!vel) { location.href = doel; return; }

    document.body.classList.add("sheet-leaving");

    var gegaan = false;
    function ga() {
      if (gegaan) return;
      gegaan = true;
      location.href = doel;
    }

    vel.addEventListener("animationend", function (ev) {
      // animationend bubbelt: alleen luisteren naar het vel zelf.
      if (ev.target === vel) ga();
    });
    // Vangnet, mocht de animatie niet lopen (of niet eindigen).
    setTimeout(ga, 600);
  });
})();
