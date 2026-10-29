// Live search and filter pills on the encyclopedia page (encyclopedia/templates/encyclopedia.html),
// without reloading the page. Works like event_filters.js on the Events page.
// The pill links and the search form also work without this file, they just reload the page.

const results = document.getElementById('plant-results');
const searchForm = document.getElementById('plant-search-form');
const searchInput = document.getElementById('plant-search');
const categoryInput = searchForm.querySelector('input[name="category"]');
const difficultyInput = searchForm.querySelector('input[name="difficulty"]');

let latestRequest = 0; // so an old, slow response can't replace newer results
let typingTimer = null;

// "?q=to&category=herbs&difficulty=easy", leaving out anything empty (same as filter_url in views.py)
function buildUrl(query, category, difficulty) {
    const params = new URLSearchParams();
    if (query) params.set('q', query);
    if (category) params.set('category', category);
    if (difficulty) params.set('difficulty', difficulty);
    return '?' + params.toString();
}

// history: 'push' adds a new step for the back button, 'replace' changes the current one, 'none' leaves it alone
async function loadResults(query, category, difficulty, history) {
    const url = buildUrl(query, category, difficulty);
    const requestId = ++latestRequest;
    // Remember the filters, so the next search keeps them
    categoryInput.value = category;
    difficultyInput.value = difficulty;
    if (searchInput.value.trim() !== query) {
        searchInput.value = query;
    }
    if (history === 'push') {
        window.history.pushState(null, '', url);
    } else if (history === 'replace') {
        window.history.replaceState(null, '', url);
    }

    results.setAttribute('aria-busy', 'true'); // fades the results while loading (aria-busy:opacity-50)
    try {
        // &partial=1 only goes to the server, never into the address bar, so refresh loads the full page
        const response = await fetch(url + (url === '?' ? '' : '&') + 'partial=1');
        if (!response.ok) {
            throw new Error(`status ${response.status}`);
        }
        const html = await response.text();
        if (requestId === latestRequest) {
            // HTML made by Django's template (plant_results.html), so the text in it is already escaped
            results.innerHTML = html;
        }
    } catch (err) {
        // Fall back to a normal page load, but only for the newest request
        if (requestId === latestRequest) {
            window.location.href = url;
        }
    } finally {
        if (requestId === latestRequest) {
            results.removeAttribute('aria-busy');
        }
    }
}

// Read the filters out of a link or the address bar
function loadFromParams(params, history) {
    loadResults(params.get('q') || '', params.get('category') || '', params.get('difficulty') || '', history);
}

// Clicks on the category and level pills. The pill's own href already has the search and the other filter in it.
document.addEventListener('click', (event) => {
    const link = event.target.closest('a[data-plant-filter]');
    // Let Ctrl/Cmd/Shift-click open the link in a new tab like normal
    if (!link || event.ctrlKey || event.metaKey || event.shiftKey) {
        return;
    }
    event.preventDefault();
    clearTimeout(typingTimer);
    loadFromParams(new URL(link.href).searchParams, 'push');
});

// Typing: wait until the user stops for 300ms, so we don't send a request for every letter.
// replaceState, so the back button doesn't step back through every letter typed.
searchInput.addEventListener('input', () => {
    clearTimeout(typingTimer);
    typingTimer = setTimeout(() => {
        loadResults(searchInput.value.trim(), categoryInput.value, difficultyInput.value, 'replace');
    }, 300);
});

// Pressing Enter: search right away
searchForm.addEventListener('submit', (event) => {
    event.preventDefault();
    clearTimeout(typingTimer);
    loadResults(searchInput.value.trim(), categoryInput.value, difficultyInput.value, 'replace');
});

// Back/forward button: load the results for the URL we went back to
window.addEventListener('popstate', () => {
    loadFromParams(new URLSearchParams(window.location.search), 'none');
});
