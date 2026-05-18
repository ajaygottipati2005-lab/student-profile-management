(function () {
    "use strict";

    function initAppShell() {
        var sidebar = document.getElementById("app-sidebar");
        var overlay = document.getElementById("app-overlay");
        var toggle = document.getElementById("app-menu-toggle");

        if (!sidebar || !toggle) {
            return;
        }

        function setOpen(open) {
            sidebar.classList.toggle("is-open", open);
            if (overlay) {
                overlay.classList.toggle("is-visible", open);
                overlay.setAttribute("aria-hidden", open ? "false" : "true");
            }
            toggle.setAttribute("aria-expanded", open ? "true" : "false");
            document.body.classList.toggle("shell-nav-open", open);
        }

        function close() {
            setOpen(false);
        }

        toggle.addEventListener("click", function () {
            setOpen(!sidebar.classList.contains("is-open"));
        });

        if (overlay) {
            overlay.addEventListener("click", close);
        }

        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape") {
                close();
            }
        });

        sidebar.querySelectorAll(".app-nav-link").forEach(function (link) {
            link.addEventListener("click", function () {
                if (window.innerWidth < 992) {
                    close();
                }
            });
        });

        window.addEventListener("resize", function () {
            if (window.innerWidth >= 992) {
                close();
            }
        });
    }

    function initStudentShell() {
        var sidebar = document.getElementById("student-sidebar");
        var overlay = document.getElementById("sidebar-overlay");
        var toggle = document.getElementById("sidebar-toggle");

        if (!sidebar || !toggle) {
            return;
        }

        function setOpen(open) {
            sidebar.classList.toggle("is-open", open);
            if (overlay) {
                overlay.classList.toggle("is-visible", open);
                overlay.setAttribute("aria-hidden", open ? "false" : "true");
            }
            toggle.setAttribute("aria-expanded", open ? "true" : "false");
            document.body.classList.toggle("shell-nav-open", open);
        }

        function close() {
            setOpen(false);
        }

        toggle.addEventListener("click", function (e) {
            e.stopPropagation();
            setOpen(!sidebar.classList.contains("is-open"));
        });

        if (overlay) {
            overlay.addEventListener("click", close);
        }

        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape") {
                close();
            }
        });

        sidebar.querySelectorAll(".app-nav-link").forEach(function (link) {
            link.addEventListener("click", close);
        });
    }

    function initTableCards() {
        document.querySelectorAll(".table-cards-mobile").forEach(function (table) {
            var headers = [];
            table.querySelectorAll("thead th").forEach(function (th) {
                headers.push(th.textContent.trim());
            });
            table.querySelectorAll("tbody tr").forEach(function (row) {
                row.querySelectorAll("td").forEach(function (td, i) {
                    if (headers[i] && !td.getAttribute("data-label")) {
                        td.setAttribute("data-label", headers[i]);
                    }
                });
            });
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        initAppShell();
        initStudentShell();
        initTableCards();
    });
})();
