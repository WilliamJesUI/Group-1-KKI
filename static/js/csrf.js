// Shared helper for AJAX. Loaded once in base.html, so every page can use getCookie().
// Django blocks POST requests without a CSRF token. With fetch, send it in a header:
//   headers: { 'X-CSRFToken': getCookie('csrftoken') }
// See docs/TEAM-GUIDE.md, section "Sending data with fetch".

// Read a cookie value, used to get the CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
