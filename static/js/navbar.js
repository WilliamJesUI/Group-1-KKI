// Show or hide the navbar menu on small screens
const navToggle = document.getElementById('nav-toggle');
const navMenu = document.getElementById('nav-menu');

navToggle.addEventListener('click', () => {
    navMenu.classList.toggle('hidden');
    const isOpen = !navMenu.classList.contains('hidden');
    navToggle.setAttribute('aria-expanded', isOpen);
});
