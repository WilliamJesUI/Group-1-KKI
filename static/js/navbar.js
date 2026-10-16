// Open or close the navbar menu on small screens
const navToggle = document.getElementById('nav-toggle');
const navMenu = document.getElementById('nav-menu');

navToggle.addEventListener('click', () => {
    // Adds data-open if it's missing, removes it if it's there. Returns true when the menu is now open.
    const isOpen = navMenu.toggleAttribute('data-open');
    navToggle.setAttribute('aria-expanded', isOpen);
    navToggle.setAttribute('aria-label', isOpen ? 'Close menu' : 'Open menu');
});
