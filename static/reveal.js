/* Load-in op scroll voor de homepage: de kaarten (hero/features/listings) en
   de voorwoord-kolom starten hun animatie pas zodra ze in beeld komen, niet
   meteen bij het laden. De losse elementen (.reveal/.tw-word/.tw-cursor)
   staan in style.css standaard "paused" met hun eigen --d-vertraging; deze
   observer zet ze op "running" door de kaart zelf .in-view te geven zodra
   hij voor een stuk zichtbaar is — de bestaande vertragingen binnen een kaart
   blijven zo intact, ze tellen nu vanaf het moment van in beeld komen. */
(function () {
  "use strict";

  var kaarten = document.querySelectorAll(
    ".hero, .feature, .listing, .voorwoord-kolom");
  if (!kaarten.length) return;

  if (!("IntersectionObserver" in window)) {
    // Zonder observer-ondersteuning gewoon alles meteen tonen.
    kaarten.forEach(function (el) { el.classList.add("in-view"); });
    return;
  }

  var observer = new IntersectionObserver(function (entries, obs) {
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

  kaarten.forEach(function (el) { observer.observe(el); });
})();
