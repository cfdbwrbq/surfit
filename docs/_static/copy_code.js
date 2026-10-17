/*
 * Adds a "Copy" button to every code block.
 *
 * The clipboard API is only available in a secure context (https or
 * localhost), and the documentation is often opened straight from disk, so
 * there is a fallback through a temporary textarea and execCommand.  The button
 * label follows the language of the page.
 */
(function () {
    "use strict";

    var language = (document.documentElement.getAttribute("lang") || "en")
        .slice(0, 2);
    var labels = language === "ru"
        ? {copy: "Копировать", copied: "Скопировано",
           title: "Скопировать код в буфер обмена"}
        : {copy: "Copy", copied: "Copied",
           title: "Copy the code to the clipboard"};

    function fallbackCopy(text) {
        var area = document.createElement("textarea");
        area.value = text;
        area.setAttribute("readonly", "");
        area.style.position = "fixed";
        area.style.top = "-1000px";
        document.body.appendChild(area);
        area.select();
        var copied = false;
        try {
            copied = document.execCommand("copy");
        } catch (error) {
            copied = false;
        }
        document.body.removeChild(area);
        return copied;
    }

    function copyText(text) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            return navigator.clipboard.writeText(text).catch(function () {
                fallbackCopy(text);
            });
        }
        fallbackCopy(text);
        return Promise.resolve();
    }

    function addButton(block) {
        var pre = block.querySelector("pre");
        if (!pre || block.querySelector(".surfit-copy")) {
            return;
        }

        var button = document.createElement("button");
        button.type = "button";
        button.className = "surfit-copy";
        button.textContent = labels.copy;
        button.title = labels.title;
        button.setAttribute("aria-label", labels.title);

        var timer = null;
        button.addEventListener("click", function () {
            copyText(pre.textContent).then(function () {
                button.textContent = labels.copied;
                button.classList.add("copied");
                if (timer) {
                    clearTimeout(timer);
                }
                timer = setTimeout(function () {
                    button.textContent = labels.copy;
                    button.classList.remove("copied");
                    timer = null;
                }, 1500);
            });
        });

        block.appendChild(button);
    }

    function addButtons() {
        var blocks = document.querySelectorAll(".highlight");
        Array.prototype.forEach.call(blocks, addButton);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", addButtons);
    } else {
        addButtons();
    }
})();
