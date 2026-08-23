/* De voet staat vast onderin het scherm (position: fixed) en de rest van de
   pagina (.page-shell) reserveert onderaan precies zoveel ruimte als de voet
   hoog is, zodat die pas zichtbaar wordt op het allerlaatste stukje scrollen
   — de voet zelf verschuift niet mee. Die hoogte verschilt sterk per breedte
   (drie kolommen worden er één op een telefoon), dus meten in plaats van een
   vaste waarde aanhouden. */
(function () {
  "use strict";

  var voet = document.querySelector("body > footer");
  if (!voet) return;

  function meet() {
    document.documentElement.style.setProperty("--footer-h", voet.offsetHeight + "px");
  }

  meet();
  window.addEventListener("resize", meet);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(meet);
})();
