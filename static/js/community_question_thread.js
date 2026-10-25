document.addEventListener('click', async (event) => {
    const button = event.target.closest('[data-vote-url]');
    if (!button || button.disabled) return;

    button.disabled = true; // blocks double-clicks while the request runs
    try {
        const response = await fetch(button.dataset.voteUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
        });
        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            const title = response.status === 403 ? 'Log in to vote' : 'Could not vote';
            showToast(title, data.message || 'Please try again.', 'error');
            return;
        }

        button.setAttribute('aria-pressed', data.voted);
        button.closest('[data-answer-card]').querySelector('[data-count]').textContent = data.score;
    } catch (error) {
        console.error('Error voting:', error);
        showToast('Network error', 'Please try again.', 'error');
    } finally {
        button.disabled = false;
    }
});

(() => {
    const cards = document.getElementById('answer-cards');
    const pills = document.querySelectorAll('#answer-filter-pills [data-filter]');
    if (!cards || pills.length === 0) return;

    const DEFAULT_FILTER = 'most_helpful';   // must match the view's default
    let latestAnswerRequest = 0;

    function buildUrl(filter) {
        return '?' + new URLSearchParams({ filter }).toString();
    }

    function showSelected(filter) {
        pills.forEach((pill) => {
            if (pill.dataset.filter === filter) {
                pill.setAttribute('aria-current', 'page');
            } else {
                pill.removeAttribute('aria-current');
            }
        });
    }

    async function loadAnswerCards(filter, historyMode) {
        const url = buildUrl(filter);
        const requestId = ++latestAnswerRequest;
        showSelected(filter);

        if (historyMode === 'push') {
            window.history.pushState(null, '', url);
        } else if (historyMode === 'replace') {
            window.history.replaceState(null, '', url);
        }

        cards.setAttribute('aria-busy', 'true');
        try {
            const response = await fetch(url + '&partial=1');
            if (!response.ok) {
                throw new Error(`status ${response.status}`);
            }
            const html = await response.text();
            if (requestId === latestAnswerRequest) {
                cards.innerHTML = html;

                const marker = cards.querySelector('[data-answer-count]');
                if (marker) {
                    const n = Number(marker.dataset.answerCount);
                    document.querySelectorAll('[data-answer-count-label]').forEach((el) => {
                        el.textContent = n === 0
                            ? (el.dataset.emptyText || 'No answers yet')
                            : `${n} answer${n === 1 ? '' : 's'}`;
                    });
                }
            }
        } catch (error) {
            console.error('Error loading answers:', error);
            if (requestId === latestAnswerRequest) {
                window.location.href = url;
            }
        } finally {
            if (requestId === latestAnswerRequest) {
                cards.removeAttribute('aria-busy');
            }
        }
    }

    document.addEventListener('click', (event) => {
        const link = event.target.closest('#answer-filter-pills [data-filter]');
        if (!link || event.ctrlKey || event.metaKey || event.shiftKey) return;
        event.preventDefault();
        loadAnswerCards(link.dataset.filter, 'push');
    });

    window.addEventListener('popstate', () => {
        const filter = new URLSearchParams(window.location.search).get('filter') || DEFAULT_FILTER;
        loadAnswerCards(filter, 'none');
    });

    window.reloadAnswerCards = () => {
        const filter = new URLSearchParams(window.location.search).get('filter') || DEFAULT_FILTER;
        return loadAnswerCards(filter, 'none');
    };

})();
