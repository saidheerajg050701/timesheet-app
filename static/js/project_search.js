// The project search box (Change 10b, D-157; shared with Reports → Project hours, D-161).
// A combobox: the server lists and sorts the projects (the address is the closest
// data-projects-url); this only shows the list, moves through it (↑/↓, Enter, Esc, click) and
// keeps the chosen id in the hidden new-project field, then announces "project-chosen" so the
// page can react (the grid fills its Task list, the report adds a project). The server checks
// every project again when it is used.
(function () {
  function combo(input) {
    var field = input.closest("[data-role=new-project-field]");
    return {
      input: input,
      list: document.getElementById(input.getAttribute("aria-controls")),
      value: field.querySelector("[data-role=new-project]"),
      status: field.querySelector("[data-role=project-count]"),
    };
  }

  function comboOptions(box) {
    return Array.prototype.slice.call(box.list.querySelectorAll("[role=option]"));
  }

  function setActive(box, option) {
    comboOptions(box).forEach(function (o) {
      o.classList.toggle("is-active", o === option);
      o.setAttribute("aria-selected", o === option ? "true" : "false");
    });
    if (option) {
      box.input.setAttribute("aria-activedescendant", option.id);
      option.scrollIntoView({ block: "nearest" });
    } else {
      box.input.removeAttribute("aria-activedescendant");
    }
  }

  function showList(box, show) {
    box.list.hidden = !show;
    box.input.setAttribute("aria-expanded", show ? "true" : "false");
    if (!show) setActive(box, null);
  }

  function searchProjects(box, then) {
    // The box still showing the chosen project means "show me the list", not a search.
    var typed = box.input.value.trim();
    var query = box.value.value && typed === box.input.dataset.chosen ? "" : typed;
    var seq = String(Number(box.input.dataset.seq || 0) + 1);
    box.input.dataset.seq = seq;
    var url = box.input.closest("[data-projects-url]").dataset.projectsUrl;
    fetch(url + "?q=" + encodeURIComponent(query), { credentials: "same-origin" })
      .then(function (response) { return response.ok ? response.text() : ""; })
      .then(function (html) {
        if (box.input.dataset.seq !== seq) return; // an older answer arriving late
        box.list.innerHTML = html;
        var options = comboOptions(box);
        options.forEach(function (o) { o.id = box.list.id + "-" + o.dataset.value; });
        box.status.textContent = options.length
          ? options.length + (options.length === 1 ? " project" : " projects")
          : "No matching project";
        showList(box, true);
        var current = options.filter(function (o) { return o.dataset.value === box.value.value; })[0];
        if (current) current.scrollIntoView({ block: "nearest" });
        if (then) then(options);
      });
  }

  function chooseProject(box, option) {
    box.value.value = option.dataset.value;
    box.input.value = option.dataset.label;
    box.input.dataset.chosen = option.dataset.label;
    showList(box, false);
    announce(box, option.dataset.value, option.dataset.label);
  }

  function announce(box, value, label) {
    box.input.dispatchEvent(new CustomEvent("project-chosen", {
      bubbles: true, detail: { value: value, label: label },
    }));
  }

  function moveActive(box, step) {
    var options = comboOptions(box);
    if (!options.length) return;
    var at = options.indexOf(box.list.querySelector(".is-active"));
    var next = at < 0 ? (step > 0 ? 0 : options.length - 1)
      : Math.min(Math.max(at + step, 0), options.length - 1);
    setActive(box, options[next]);
  }

  function reset(field) {
    // Back to the project the page was drawn with (the grid's ⋮ Change row), or empty.
    var input = field.querySelector("[data-role=project-search]");
    var box = combo(input);
    box.value.value = box.value.dataset.initial || "";
    input.value = input.defaultValue;
    input.dataset.chosen = input.defaultValue;
    showList(box, false);
  }
  window.ProjectSearch = { reset: reset };

  var searchTimer = null;

  document.addEventListener("keydown", function (event) {
    var input = event.target.closest && event.target.closest("[data-role=project-search]");
    if (!input) return;
    var box = combo(input);
    var open = !box.list.hidden;
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      var step = event.key === "ArrowDown" ? 1 : -1;
      if (open) moveActive(box, step);
      else searchProjects(box, function () { moveActive(box, step); });
    } else if (event.key === "Enter") {
      event.preventDefault(); // never submits the form (the week, the report filters)
      var active = box.list.querySelector(".is-active");
      if (open && active) chooseProject(box, active);
    } else if (event.key === "Escape" && open) {
      event.preventDefault(); // closes the list only; a second Esc closes the dialog
      event.stopPropagation();
      showList(box, false);
    } else if (event.key === "Tab") {
      showList(box, false);
    }
  });

  document.addEventListener("input", function (event) {
    if (!event.target.matches("[data-role=project-search]")) return;
    var box = combo(event.target);
    if (box.value.value && event.target.value !== box.input.dataset.chosen) {
      box.value.value = ""; // typing again: choose again ("Choose a project.")
      announce(box, "", "");
    }
    clearTimeout(searchTimer);
    searchTimer = setTimeout(function () { searchProjects(box); }, 150);
  });

  document.addEventListener("mousedown", function (event) {
    // Keep the focus in the box while an option is clicked or tapped.
    if (event.target.closest(".project-combo-list")) event.preventDefault();
  });

  document.addEventListener("click", function (event) {
    var option = event.target.closest(".project-combo-list [role=option]");
    if (option) {
      var input = option.closest("[data-role=new-project-field]").querySelector("[data-role=project-search]");
      chooseProject(combo(input), option);
      input.focus();
    } else if (event.target.matches("[data-role=project-search]")) {
      var box = combo(event.target);
      if (box.list.hidden) searchProjects(box);
    }
  });

  document.addEventListener("focusout", function (event) {
    var field = event.target.closest && event.target.closest("[data-role=new-project-field]");
    if (field && !field.contains(event.relatedTarget)) {
      showList(combo(field.querySelector("[data-role=project-search]")), false);
    }
  });
})();
