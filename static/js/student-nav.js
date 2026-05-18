(function () {
    "use strict";

    function initStudentNav() {
        var sidebar = document.getElementById("student-sidebar");
        var overlay = document.getElementById("sidebar-overlay");
        var toggleBtn = document.getElementById("sidebar-toggle");

        if (!sidebar || !overlay || !toggleBtn) {
            return;
        }

        function setOpen(isOpen) {
            sidebar.classList.toggle("is-open", isOpen);
            overlay.classList.toggle("is-visible", isOpen);
            toggleBtn.setAttribute("aria-expanded", isOpen ? "true" : "false");
            overlay.setAttribute("aria-hidden", isOpen ? "false" : "true");
            document.body.classList.toggle("sidebar-open", isOpen);
        }

        function openSidebar() {
            setOpen(true);
        }

        function closeSidebar() {
            setOpen(false);
        }

        function toggleSidebar() {
            setOpen(!sidebar.classList.contains("is-open"));
        }

        toggleBtn.addEventListener("click", function (event) {
            event.stopPropagation();
            toggleSidebar();
        });

        overlay.addEventListener("click", closeSidebar);

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                closeSidebar();
            }
        });

        sidebar.querySelectorAll(".sidebar-nav a").forEach(function (link) {
            link.addEventListener("click", closeSidebar);
        });

        window.addEventListener("resize", function () {
            if (window.innerWidth >= 1024 && sidebar.classList.contains("is-open")) {
                closeSidebar();
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initStudentNav);
    } else {
        initStudentNav();
    }
})();
