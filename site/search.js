/* Zoeken en rubrieken-menu voor De Dissident. */
(function () {
  "use strict";

  var prefix = location.pathname.indexOf("/artikel/") !== -1 ? "../" : "";
  var index = null;

  var loading = null;

  function load() {
    if (index) return Promise.resolve(index);
    if (window.DD_INDEX) {
      index = window.DD_INDEX;
      return Promise.resolve(index);
    }
    if (loading) return loading;
    // Injecting a <script> rather than fetching keeps this working over
    // file://, where fetch() is blocked — and loading it on first use keeps
    // the index off the critical path of every page.
    loading = new Promise(function (resolve) {
      var s = document.createElement("script");
      s.src = prefix + "search-index.js";
      s.onload = function () {
        index = window.DD_INDEX || [];
        resolve(index);
      };
      s.onerror = function () { resolve([]); };
      document.head.appendChild(s);
    });
    return loading;
  }

  function norm(s) {
    return (s || "").toLowerCase()
      .normalize("NFD").replace(/[̀-ͯ]/g, "");
  }

  function score(item, terms) {
    var hay = {
      t: norm(item.t), s: norm(item.s), c: norm(item.c),
      a: norm(item.a), x: norm(item.x)
    };
    var total = 0;
    for (var i = 0; i < terms.length; i++) {
      var q = terms[i], s = 0;
      if (hay.t.indexOf(q) !== -1) s += 10;
      if (hay.s.indexOf(q) !== -1) s += 5;
      if (hay.a.indexOf(q) !== -1) s += 4;
      if (hay.c.indexOf(q) !== -1) s += 3;
      if (hay.x.indexOf(q) !== -1) s += 1;
      if (s === 0) return 0;          // elk woord moet ergens voorkomen
      total += s;
    }
    return total;
  }

  /* ---------------- zoeken: quick-access-archief ----------------
     De zoekbalk opent een bedekkend overlay-scherm dat het archief nabootst
     (zelfde .section-heading/.toc opmaak, per editie gegroepeerd). Leeg
     toont hij de hele index — bladermodus; typen filtert live. */

  var input = document.getElementById("q");
  var overlay = document.getElementById("search-overlay");
  var overlayResults = document.getElementById("search-overlay-results");
  var overlayIntro = document.getElementById("search-overlay-intro");
  var overlayClose = document.getElementById("search-overlay-close");
  var overlayField = document.getElementById("search-overlay-field");
  var status = document.getElementById("search-status");

  // De .search-form (invoerveld + icoon) verhuist tussen de nav en de
  // overlay, zodat je altijd ziet wat je typt — ook als de overlay eroverheen
  // ligt. navHome onthoudt waar hij vandaan kwam, om terug te zetten.
  var searchForm = input ? input.closest(".search") : null;
  var navHome = searchForm ? searchForm.parentNode : null;

  function announce(msg) {
    if (status) status.textContent = msg;
  }

  function esc(s) {
    return (s || "").replace(/[<>&]/g, function (c) {
      return c === "<" ? "&lt;" : c === ">" ? "&gt;" : "&amp;";
    });
  }

  function show(open) {
    overlay.hidden = !open;
    if (input) input.setAttribute("aria-expanded", open ? "true" : "false");
    document.body.style.overflow = open ? "hidden" : "";
    if (open) {
      if (searchForm && overlayField && searchForm.parentNode !== overlayField) {
        overlayField.appendChild(searchForm);
        input.focus();
      }
      overlay.scrollTop = 0;
    } else {
      if (searchForm && navHome && searchForm.parentNode !== navHome) {
        navHome.appendChild(searchForm);
      }
      input.blur();
    }
  }

  function render(list, query, editions) {
    if (query && !list.length) {
      overlayIntro.textContent = "Geen artikelen gevonden voor “" + query + "”.";
      overlayResults.innerHTML = "";
      announce("Geen artikelen gevonden.");
      return;
    }
    overlayIntro.textContent = query
      ? list.length + (list.length === 1 ? " artikel" : " artikelen") + ' gevonden voor “' + query + '”.'
      : "Alle edities van De Dissident, met alle artikelen.";

    var byEdition = {};
    list.forEach(function (r) {
      (byEdition[r.e] = byEdition[r.e] || []).push(r);
    });

    overlayResults.innerHTML = editions
      .filter(function (ed) { return byEdition[ed.n]; })
      .map(function (ed) {
        var theme = ed.t ? " — " + esc(ed.t) : "";
        var items = byEdition[ed.n].map(function (r) {
          var sub = r.s ? '<span class="toc-sub">' + esc(r.s) + "</span>" : "";
          return '<li><span class="toc-main"><a href="' + prefix + r.u + '">' +
            esc(r.t) + "</a>" + sub + '</span><span class="toc-author">' +
            esc(r.a) + "</span></li>";
        }).join("");
        return '<section class="section-heading">' +
          "<h2>" + ed.n + "<sup>e</sup> editie" + theme + "</h2>" +
          '<div class="rule"></div>' +
          '<a class="section-link" href="' + prefix + ed.u + '">' + esc(ed.l) + "</a>" +
          "</section>" +
          '<ul class="toc">' + items + "</ul>";
      }).join("");

    announce(query
      ? list.length + (list.length === 1 ? " artikel" : " artikelen") + " gevonden."
      : "Volledig archief geladen.");
  }

  function run() {
    var query = input.value.trim();
    show(true);
    load().then(function (data) {
      var editions = window.DD_EDITIONS || [];
      if (!query) { render(data, "", editions); return; }
      var terms = norm(query).split(/\s+/).filter(Boolean);
      var hits = data
        .map(function (it) { return { it: it, sc: score(it, terms) }; })
        .filter(function (h) { return h.sc > 0; })
        .sort(function (a, b) { return b.sc - a.sc; })
        .map(function (h) { return h.it; });
      render(hits, query, editions);
    });
  }

  if (input && overlay) {
    var timer;
    input.addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(run, 120);
    });
    input.addEventListener("focus", run);
    overlayClose.addEventListener("click", function () { show(false); });
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) show(false);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !overlay.hidden) show(false);
    });
  }

  /* ---------- rubriekfilter op het archief ----------
     Geen menu meer om deze links te genereren (de navigatie is gesnoeid tot
     alleen de zoekbalk), maar een bestaande of gedeelde archief.html?rubriek=
     link moet blijven werken — vandaar dat deze logica blijft staan. */

  var wanted = new URLSearchParams(location.search).get("rubriek");
  if (wanted) {
    // markeer de actieve rubriek zichtbaar boven de pagina (niet de
    // gelijknamige .page-intro binnen de zoek-overlay, die elders in de DOM
    // zit maar wel matcht op een kale .page-intro selector)
    var intro = document.querySelector("#inhoud .page-intro");
    if (intro) {
      intro.innerHTML = 'Rubriek: <strong>' + wanted.replace(/[<>&]/g, "") +
        '</strong> — <a class="reset-filter" href="archief.html">toon alles</a>';
    }
    load().then(function (data) {
      var urls = {};
      data.forEach(function (r) { if (r.c === wanted) urls[r.u] = true; });
      Array.prototype.forEach.call(document.querySelectorAll(".toc li"), function (li) {
        var a = li.querySelector("a");
        var href = a ? a.getAttribute("href") : "";
        if (!urls[href]) li.style.display = "none";
      });
      Array.prototype.forEach.call(document.querySelectorAll(".toc"), function (ul) {
        var any = Array.prototype.some.call(ul.querySelectorAll("li"), function (li) {
          return li.style.display !== "none";
        });
        if (!any) {
          ul.style.display = "none";
          var head = ul.previousElementSibling;
          if (head && head.classList.contains("section-heading")) head.style.display = "none";
        }
      });
    });
  }
})();
