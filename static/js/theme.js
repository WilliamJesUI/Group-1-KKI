// Light/dark mode switch (the moon/sun button from templates/theme_toggle.html).
// base.html already adds the "dark" class to <html> before the page paints if the saved choice is dark,
// so this file only handles clicks and keeps the icon and label in sync.
(function () {
  const root = document.documentElement;

  function syncButtons() {
    const dark = root.classList.contains("dark");
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
      button.setAttribute("aria-pressed", dark ? "true" : "false");
      button.querySelector('[data-theme-icon="moon"]').classList.toggle("hidden", dark);
      button.querySelector('[data-theme-icon="sun"]').classList.toggle("hidden", !dark);
    });
  }

  document.addEventListener("click", (event) => {
    if (!event.target.closest("[data-theme-toggle]")) return;
    const dark = root.classList.toggle("dark");
    try {
      localStorage.setItem("gyg-theme", dark ? "dark" : "light");
    } catch (error) {
      // Private windows can block storage. The switch still works for this page.
    }
    syncButtons();
  });

  syncButtons();
})();
