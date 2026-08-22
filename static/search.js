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

  /* ---------------- zoeken ---------------- */

  var input = document.getElementById("q");
  var results = document.getElementById("search-results");
  var status = document.getElementById("search-status");

  function announce(msg) {
    if (status) status.textContent = msg;
  }

  function show(open) {
    results.hidden = !open;
    if (input) input.setAttribute("aria-expanded", open ? "true" : "false");
  }

  function render(list, query) {
    if (!list.length) {
      results.innerHTML = '<p class="search-empty">Geen artikelen gevonden voor “' +
        query.replace(/[<>&]/g, "") + '”.</p>';
      show(true);
      announce("Geen artikelen gevonden.");
      return;
    }
    var shown = list.slice(0, 12);
    results.innerHTML = shown.map(function (r) {
      return '<a href="' + prefix + r.u + '" role="option">' +
        '<span class="r-title">' + r.t + "</span>" +
        '<span class="r-meta">' + r.c + " · " + r.a +
        " · editie " + r.e + "</span></a>";
    }).join("");
    show(true);
    announce(list.length + (list.length === 1 ? " artikel" : " artikelen") +
      " gevonden" + (list.length > shown.length ? ", eerste " + shown.length + " getoond" : "") + ".");
  }

  function run() {
    var query = input.value.trim();
    if (query.length < 2) { show(false); announce(""); return; }
    load().then(function (data) {
      var terms = norm(query).split(/\s+/).filter(Boolean);
      var hits = data
        .map(function (it) { return { it: it, sc: score(it, terms) }; })
        .filter(function (h) { return h.sc > 0; })
        .sort(function (a, b) { return b.sc - a.sc; })
        .map(function (h) { return h.it; });
      render(hits, query);
    });
  }

  if (input && results) {
    var timer;
    input.addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(run, 120);
    });
    input.addEventListener("focus", function () {
      if (input.value.trim().length >= 2) run();
    });
    document.addEventListener("click", function (e) {
      if (!results.contains(e.target) && e.target !== input) show(false);
    });
    input.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { show(false); input.blur(); }
    });
  }

  /* ---------- rubriekfilter op het archief ----------
     Geen menu meer om deze links te genereren (de navigatie is gesnoeid tot
     alleen de zoekbalk), maar een bestaande of gedeelde archief.html?rubriek=
     link moet blijven werken — vandaar dat deze logica blijft staan. */

  var wanted = new URLSearchParams(location.search).get("rubriek");
  if (wanted) {
    // markeer de actieve rubriek zichtbaar boven de pagina
    var intro = document.querySelector(".page-intro");
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
