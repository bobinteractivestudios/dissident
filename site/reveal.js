/* Load-in op scroll: de kaarten (hero/features/listings) en de voorwoord-kolom
   starten hun animatie pas zodra ze in beeld komen, niet meteen bij het laden.
   De losse elementen (.reveal/.tw-word/.tw-cursor) staan in style.css
   standaard "paused" met hun eigen --d-vertraging; deze observer zet ze op
   "running" door de kaart zelf .in-view te geven zodra hij voor een stuk
   zichtbaar is — de vertragingen binnen een kaart blijven zo intact, ze tellen
   vanaf het moment van in beeld komen.

   Wordt ook opnieuw gedraaid na het wisselen van editie (edition.js vuurt
   dan dd:swap af), want die inhoud is dan volledig vervangen. */
(function () {
  "use strict";

  var observer = null;

  function maakObserver() {
    if (!("IntersectionObserver" in window)) return null;
    return new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("in-view");
        obs.unobserve(entry.target);
      });
    }, {
      // Iets voordat een kaart de onderrand van het scherm haalt, niet pas
      // wanneer hij al volledig in beeld staat.
      rootMargin: "0px 0px -10% 0px",
      threshold: 0.15
    });
  }

  function scan() {
    var kaarten = document.querySelectorAll(
      ".hero, .feature, .listing, .voorwoord-kolom");
    if (!kaarten.length) return;

    if (!observer) observer = maakObserver();
    if (!observer) {
      // Zonder observer-ondersteuning gewoon alles meteen tonen.
      Array.prototype.forEach.call(kaarten, function (el) {
        el.classList.add("in-view");
      });
      return;
    }
    Array.prototype.forEach.call(kaarten, function (el) {
      if (!el.classList.contains("in-view")) observer.observe(el);
    });
  }

  // Het vel kantelt bij elke lading én bij elke wissel binnen (sheet-in in
  // style.css). Zolang dat loopt niets laten verschijnen, anders schuiven de
  // kaarten door de kantelbeweging heen. Wat later in beeld gescrold wordt is
  // dan allang voorbij dit punt en heeft er geen last van.
  function startNaVel() {
    var vel = document.querySelector("main.expo");
    if (!vel) { scan(); return; }

    var begonnen = false;
    function kick() {
      if (begonnen) return;
      begonnen = true;
      scan();
    }

    vel.addEventListener("animationend", function (e) {
      // animationend bubbelt: alleen op het vel zelf reageren.
      if (e.target === vel) kick();
    });
    // Vangnet, mocht sheet-in niet lopen of niet eindigen.
    setTimeout(kick, 800);
  }

  startNaVel();
  document.addEventListener("dd:swap", startNaVel);
})();
