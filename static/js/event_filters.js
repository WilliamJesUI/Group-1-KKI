// Filter pills and search on the events page (events/templates/event_list.html), without reloading the page.
// The links and the search form also work without this file, they just reload the page.

const cards = document.getElementById('event-cards');
const pills = document.querySelectorAll('#event-filter-pills [data-filter]');
const searchForm = document.getElementById('event-search-form');
const searchInput = document.getElementById('event-search');
const filterInput = searchForm.querySelector('input[name="filter"]');

let latestRequest = 0; // so an old, slow response can't replace newer cards
let typingTimer = null;

// "?filter=month&q=seed" for the address bar and the pill links
function buildUrl(filter, query) {
    const params = new URLSearchParams({ filter: filter });
    if (query) {
        params.set('q', query);
    }
    return '?' + params.toString();
}

// Point each pill link at its filter plus the search, so switching pills keeps the search
function updatePillLinks(query) {
    pills.forEach((pill) => {
        pill.href = buildUrl(pill.dataset.filter, query);
    });
}

// Make the pills and the search box match the filter and search being shown
function showSelected(filter, query) {
    pills.forEach((pill) => {
        if (pill.dataset.filter === filter) {
            pill.setAttribute('aria-current', 'page');
        } else {
            pill.removeAttribute('aria-current');
        }
    });
    updatePillLinks(query);
    filterInput.value = filter;
    if (searchInput.value.trim() !== query) {
        searchInput.value = query;
    }
}

// history: 'push' adds a new step for the back button, 'replace' changes the current one, 'none' leaves it alone
async function loadCards(filter, query, history) {
    const url = buildUrl(filter, query);
    const requestId = ++latestRequest;
    showSelected(filter, query);
    if (history === 'push') {
        window.history.pushState(null, '', url);
    } else if (history === 'replace') {
        window.history.replaceState(null, '', url);
    }

    cards.setAttribute('aria-busy', 'true'); // fades the cards while loading (aria-busy:opacity-50)
    try {
        // &partial=1 only goes to the server, never into the address bar, so the back button
        // and refresh always load the full page instead of just the cards
        const response = await fetch(url + '&partial=1');
        if (!response.ok) {
            throw new Error(`status ${response.status}`);
        }
        const html = await response.text();
        if (requestId === latestRequest) {
            // HTML made by Django's template, so the text in it is already escaped.
            // The new cards fade in by themselves (starting:opacity-0 in event_cards.html).
            cards.innerHTML = html;
        }
    } catch (err) {
        // Fall back to a normal page load, but only for the newest request. An older one was already
        // replaced, and reloading it would jump back to a filter the user already left.
        if (requestId === latestRequest) {
            window.location.href = url;
        }
    } finally {
        if (requestId === latestRequest) {
            cards.removeAttribute('aria-busy');
        }
    }
}

// Clicks on the pills, and on "See upcoming events" / "Clear search" inside the cards.
// The link's own href says which filter and search to load.
document.addEventListener('click', (event) => {
    const link = event.target.closest('a[data-filter]');
    // Let Ctrl/Cmd/Shift-click open the link in a new tab like normal
    if (!link || event.ctrlKey || event.metaKey || event.shiftKey) {
        return;
    }
    event.preventDefault();
    clearTimeout(typingTimer); // the link already has the typed search in it, so don't run the search again
    const params = new URL(link.href).searchParams;
    loadCards(params.get('filter') || 'upcoming', params.get('q') || '', 'push');
});

// Typing: wait until the user stops for 300ms, so we don't send a request for every letter.
// replaceState, so the back button doesn't step back through every letter typed.
searchInput.addEventListener('input', () => {
    // Update the pill links right away, so a pill clicked before the search runs keeps the typed text
    updatePillLinks(searchInput.value.trim());
    clearTimeout(typingTimer);
    typingTimer = setTimeout(() => {
        loadCards(filterInput.value, searchInput.value.trim(), 'replace');
    }, 300);
});

// Pressing Enter: search right away
searchForm.addEventListener('submit', (event) => {
    event.preventDefault();
    clearTimeout(typingTimer);
    loadCards(filterInput.value, searchInput.value.trim(), 'replace');
});

// Back/forward button: load the cards for the URL we went back to
window.addEventListener('popstate', () => {
    const params = new URLSearchParams(window.location.search);
    loadCards(params.get('filter') || 'upcoming', params.get('q') || '', 'none');
});
