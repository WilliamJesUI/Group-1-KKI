// Filter pills and search on the community page (community/templates/question_list.html),
// without reloading the page.
// The pill links and the search form also work without this file; they just reload the page.

(function () {
    const cards = document.getElementById('question-cards');
    const searchForm = document.getElementById('question-search-form');
    const searchInput = document.getElementById('question-search');

    // Not on this page, so do nothing
    if (!cards || !searchForm || !searchInput) {
        return;
    }

    const pills = document.querySelectorAll('#question-filter-pills [data-filter]');
    const filterInput = searchForm.querySelector('input[name="filter"]');
    const plantInput = searchForm.querySelector('input[name="plant"]');
    const DEFAULT_FILTER = 'latest';

    let latestRequest = 0; // so an old, slow response can't replace newer cards
    let typingTimer = null;

    // "?filter=popular&q=tomato" for the address bar and the pill links
    function buildUrl(filter, query) {
        const params = new URLSearchParams({ filter: filter });
        if (query) {
            params.set('q', query);
        }
        // Keep the plant from the Popular Plants box, so search and pills stay inside that plant
        if (plantInput && plantInput.value) {
            params.set('plant', plantInput.value);
        }
        return '?' + params.toString();
    }

    // Point each pill at its own filter plus the current search
    function updatePillLinks(query) {
        pills.forEach((pill) => {
            pill.href = buildUrl(pill.dataset.filter, query);
        });
    }

    // Make the pills and the search box match what is being shown
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

    // history: 'push' adds a back-button step, 'replace' changes the current one, 'none' leaves it
    async function loadCards(filter, query, history) {
        const url = buildUrl(filter, query);
        const requestId = ++latestRequest;
        showSelected(filter, query);

        if (history === 'push') {
            window.history.pushState(null, '', url);
        } else if (history === 'replace') {
            window.history.replaceState(null, '', url);
        }

        cards.setAttribute('aria-busy', 'true'); // fades the cards while loading
        try {
            // &partial=1 only goes to the server, never into the address bar
            const response = await fetch(url + '&partial=1');
            if (!response.ok) {
                throw new Error('status ' + response.status);
            }
            const html = await response.text();
            if (requestId === latestRequest) {
                cards.innerHTML = html; // HTML from Django's template, already escaped
            }
        } catch (err) {
            // Fall back to a normal page load, but only for the newest request
            if (requestId === latestRequest) {
                window.location.href = url;
            }
        } finally {
            if (requestId === latestRequest) {
                cards.removeAttribute('aria-busy');
            }
        }
    }

    // Clicks on the pills, and on "Clear search" / "See latest questions" inside the cards
    document.addEventListener('click', (event) => {
        const link = event.target.closest('a[data-filter]');
        // Let Ctrl/Cmd/Shift-click open in a new tab like normal
        if (!link || event.ctrlKey || event.metaKey || event.shiftKey) {
            return;
        }
        event.preventDefault();
        clearTimeout(typingTimer);
        const params = new URL(link.href).searchParams;
        loadCards(params.get('filter') || DEFAULT_FILTER, params.get('q') || '', 'push');
    });

    // Typing: wait 300ms after the user stops, so we don't send a request per letter
    searchInput.addEventListener('input', () => {
        updatePillLinks(searchInput.value.trim()); // pills keep the typed text right away
        clearTimeout(typingTimer);
        typingTimer = setTimeout(() => {
            loadCards(filterInput.value, searchInput.value.trim(), 'replace');
        }, 300);
    });

    // Enter key: search right away
    searchForm.addEventListener('submit', (event) => {
        event.preventDefault();
        clearTimeout(typingTimer);
        loadCards(filterInput.value, searchInput.value.trim(), 'replace');
    });

    // Back/forward button: load the cards for the URL we went back to
    window.addEventListener('popstate', () => {
        const params = new URLSearchParams(window.location.search);
        loadCards(params.get('filter') || DEFAULT_FILTER, params.get('q') || '', 'none');
    });

    // Lets other scripts (like question_form.js) refresh the list after posting a question:
    //   window.reloadQuestionCards();
    window.reloadQuestionCards = () => {
        const params = new URLSearchParams(window.location.search);
        loadCards(params.get('filter') || DEFAULT_FILTER, params.get('q') || '', 'none');
    };
})();