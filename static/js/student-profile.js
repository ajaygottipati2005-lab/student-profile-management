(function () {
    "use strict";

    function initProfilePhoto() {
        var avatar = document.getElementById("profile-avatar");
        var backdrop = document.getElementById("dp-menu-backdrop");
        var menu = document.getElementById("dp-menu");
        var fileInput = document.getElementById("dp-input");
        var uploadForm = document.getElementById("dp-upload-form");
        var uploadBtn = document.getElementById("dp-upload-device");
        var changeBtn = document.getElementById("dp-change-picture");
        var cancelBtn = document.getElementById("dp-menu-cancel");

        if (!avatar || !fileInput || !uploadForm) {
            return;
        }

        function openMenu() {
            if (backdrop) backdrop.classList.add("is-open");
            if (menu) menu.classList.add("is-open");
            document.body.classList.add("shell-nav-open");
        }

        function closeMenu() {
            if (backdrop) backdrop.classList.remove("is-open");
            if (menu) menu.classList.remove("is-open");
            document.body.classList.remove("shell-nav-open");
        }

        function pickFile() {
            fileInput.click();
            closeMenu();
        }

        avatar.addEventListener("click", function (e) {
            e.preventDefault();
            openMenu();
        });

        avatar.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                openMenu();
            }
        });

        if (uploadBtn) uploadBtn.addEventListener("click", pickFile);
        if (changeBtn) changeBtn.addEventListener("click", pickFile);

        if (cancelBtn) cancelBtn.addEventListener("click", closeMenu);
        if (backdrop) backdrop.addEventListener("click", closeMenu);

        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape") closeMenu();
        });

        fileInput.addEventListener("change", function () {
            if (!fileInput.files || !fileInput.files.length) {
                return;
            }

            var img = avatar.querySelector("img");
            var placeholder = avatar.querySelector(".avatar-placeholder");

            if (img) {
                img.src = URL.createObjectURL(fileInput.files[0]);
            } else if (placeholder) {
                var preview = document.createElement("img");
                preview.alt = "Preview";
                preview.src = URL.createObjectURL(fileInput.files[0]);
                placeholder.replaceWith(preview);
            }

            uploadForm.submit();
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initProfilePhoto);
    } else {
        initProfilePhoto();
    }
})();
