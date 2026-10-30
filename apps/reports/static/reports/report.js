// Reports → Project hours (Change 11, D-160–D-163). Convenience only: the filters are a plain
// GET form (every value is checked again on the server), and the chart has a table with the
// same numbers. Chosen projects become removable chips posted as project=I-001.
(function () {
  var form = document.getElementById("report-filters");
  if (form) {
    var period = form.querySelector("[data-role=period]");
    period.addEventListener("change", function () {
      form.querySelectorAll("[data-role=custom-dates]").forEach(function (field) {
        field.hidden = period.value !== "custom";
      });
    });
    var scope = form.querySelector("[data-role=scope]");
    if (scope) {
      scope.addEventListener("change", function () {
        var field = form.querySelector("[data-role=manager-field]");
        field.hidden = scope.value !== "manager";
        field.querySelector("select").disabled = scope.value !== "manager";
      });
    }
    var chips = form.querySelector("[data-role=project-chips]");

    form.addEventListener("project-chosen", function (event) {
      var label = event.detail.label;
      if (!event.detail.value || !label) return; // typing again: nothing chosen yet
      var code = label.split(" ")[0];
      if (!chips.querySelector('input[value="' + code + '"]')) {
        var all = chips.querySelector("[data-role=all-projects]");
        if (all) all.remove();
        var chip = document.createElement("span");
        chip.className = "report-chip";
        chip.textContent = label;
        var input = document.createElement("input");
        input.type = "hidden";
        input.name = "project";
        input.value = code;
        var remove = document.createElement("button");
        remove.type = "button";
        remove.className = "btn-close btn-close-sm";
        remove.dataset.role = "remove-project";
        remove.setAttribute("aria-label", "Remove " + label);
        chip.append(input, remove);
        chips.append(chip);
      }
      window.ProjectSearch.reset(event.target.closest("[data-role=new-project-field]"));
      event.target.focus(); // ready for the next project
    });

    chips.addEventListener("click", function (event) {
      var remove = event.target.closest("[data-role=remove-project]");
      if (!remove) return;
      remove.closest(".report-chip").remove();
      if (!chips.querySelector(".report-chip")) {
        var all = document.createElement("span");
        all.className = "small text-body-secondary";
        all.dataset.role = "all-projects";
        all.textContent = "All projects";
        chips.append(all);
      }
      form.querySelector("[data-role=project-search]").focus();
    });
  }

  var source = document.getElementById("report-chart-data");
  var canvas = document.getElementById("report-chart");
  if (!source || !canvas || typeof Chart === "undefined") return;
  var data = JSON.parse(source.textContent);
  // Colours come from the theme tokens in css/theme.css (D-103), as on the dashboard.
  var tokens = getComputedStyle(document.documentElement);
  function token(name, fallback) { return tokens.getPropertyValue(name).trim() || fallback; }
  var SERIES = token("--ts-chart-series", "#2563eb");
  var MUTED = token("--ts-chart-muted", "#475569");
  var GRID = token("--ts-chart-grid", "rgba(71, 85, 105, 0.14)");
  Chart.defaults.color = MUTED;
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  new Chart(canvas, {
    type: "bar",
    data: {
      labels: data.map(function (p) { return p.label; }),
      datasets: [{ label: "Hours", data: data.map(function (p) { return p.hours; }),
        backgroundColor: SERIES, borderRadius: 4, borderSkipped: "start", maxBarThickness: 22 }],
    },
    options: {
      indexAxis: "y",
      maintainAspectRatio: false,
      scales: { x: { grid: { color: GRID }, border: { display: false }, beginAtZero: true },
        y: { grid: { display: false }, border: { display: false } } },
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: function (c) {
        return "Hours: " + Number(c.parsed.x).toFixed(2) + " h";
      } } } },
    },
  });
})();
