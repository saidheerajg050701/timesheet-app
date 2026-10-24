// Dashboard charts (FR-5). Data comes only from the json_script block #dashboard-data
// (D-80); every chart has a table with the same numbers, so nothing depends on this file.
(function () {
  var source = document.getElementById("dashboard-data");
  if (!source || typeof Chart === "undefined") return;
  var data = JSON.parse(source.textContent);

  var SERIES = "#2a78d6"; // categorical slot 1 (validated for the light surface)
  var MUTED = "#52514e"; // reference line and axis text
  var GRID = "rgba(82, 81, 78, 0.12)";
  Chart.defaults.color = MUTED;
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;

  function hours(value) {
    return Number(value).toFixed(2) + " h";
  }

  function draw(id, config) {
    var canvas = document.getElementById(id);
    if (canvas) new Chart(canvas, config);
  }

  var axis = { grid: { color: GRID }, border: { display: false }, beginAtZero: true };
  var noGrid = { grid: { display: false }, border: { display: false } };
  var tooltip = { callbacks: { label: function (c) { return c.dataset.label + ": " + hours(c.parsed[c.chart.options.indexAxis === "y" ? "x" : "y"]); } } };

  draw("hours-chart", {
    data: {
      labels: data.weeks.map(function (w) { return w.label; }),
      datasets: [
        { type: "bar", label: "Hours worked", data: data.weeks.map(function (w) { return w.worked; }),
          backgroundColor: SERIES, borderRadius: 4, borderSkipped: "bottom", maxBarThickness: 28 },
        { type: "line", label: "Expected", data: data.weeks.map(function (w) { return w.expected; }),
          borderColor: MUTED, borderDash: [6, 4], borderWidth: 2, pointRadius: 0, stepped: "middle" },
      ],
    },
    options: {
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: { y: axis, x: noGrid },
      plugins: { tooltip: tooltip, legend: { position: "bottom" } },
    },
  });

  [["projects-chart", data.projects], ["categories-chart", data.categories]].forEach(function (pair) {
    draw(pair[0], {
      type: "bar",
      data: {
        labels: pair[1].map(function (r) { return r.label; }),
        datasets: [{ label: "Hours", data: pair[1].map(function (r) { return r.hours; }),
          backgroundColor: SERIES, borderRadius: 4, borderSkipped: "start", maxBarThickness: 22 }],
      },
      options: {
        indexAxis: "y",
        maintainAspectRatio: false,
        scales: { x: axis, y: noGrid },
        plugins: { legend: { display: false }, tooltip: tooltip },
      },
    });
  });
})();
