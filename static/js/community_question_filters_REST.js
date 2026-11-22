// Filter pills and search on the community page (community/templates/question_list.html),
// without reloading the page.
// The pill links and the search form also work without this file; they just reload the page.

(function () {
    const API_URL = '/community/api/v1/questions/';

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


    // Remember the chosen plant and highlight it in the Popular Plants box
    function showPlant(slug) {
        if (!plantInput) {
            return;
        }
        plantInput.value = slug;
        document.querySelectorAll('a[data-plant]').forEach((link) => {
            if (link.dataset.plant === slug) {
                link.setAttribute('aria-current', 'true');
            } else {
                link.removeAttribute('aria-current');
            }
        });
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
            const response = await fetch(API_URL + url, {
                headers: { 'Accept': 'application/json' },
            });
            if (!response.ok) throw new Error('status ' + response.status);
            const questions = await response.json();

            if (requestId === latestRequest) {
                renderCards(questions, filter, query);
            }
        } catch (err) {
            console.error(err);

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

    // Small helper: create an element with classes and plain text
    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function buildQuestionCard(q) {
        const article = el('article', 'relative h-full overflow-hidden rounded-2xl border-2 border-ink bg-surface transition-[border-color,box-shadow,transform] duration-150 ease-out hover:border-brand hover:scale-102 hover:shadow-[4px_4px_0_0_var(--color-ink)] has-[h2_a:focus-visible]:border-brand has-[h2_a:focus-visible]:shadow-[4px_4px_0_0_var(--color-ink)]');
        const row = el('div', 'flex gap-4 p-5');

        // vote box
        const votes = el('div', 'flex size-[64px] shrink-0 flex-col items-center justify-center rounded-xl border-2 border-ink bg-brand-tint text-center');
        votes.append(
            el('span', 'text-sm font-extrabold', String(q.vote_count)),
            el('span', 'text-xs text-ink-soft', 'votes')
        );

        const content = el('div', 'min-w-0 flex-1');

        // author row
        const author = el('a', 'relative z-10 flex w-fit transition-transform duration-150 hover:scale-102 flex-wrap items-center gap-2 text-sm');
        author.href = q.author_url;
        let avatar;
        if (q.author_picture) {
            avatar = el('img', 'size-8 rounded-full object-cover');
            avatar.src = q.author_picture;
            avatar.alt = 'Profile picture of ' + q.author_name;
        } else {
            avatar = el('span', 'card-avatar ' + (q.author_avatar_class || ''), q.author_initials);
        }
        author.append(
            avatar,
            el('span', 'font-semibold', q.author_name),
            el('span', 'text-ink-soft', '· ' + q.time_ago)
        );

        // title (link covers the whole card)
        const h2 = el('h2', 'mt-1 font-display text-xl leading-[1.3]');
        const titleLink = el('a', 'after:absolute after:inset-0 focus-visible:outline-none', q.title);
        titleLink.href = q.url;
        h2.append(titleLink);

        // excerpt
        const excerpt = el('p', 'mt-1 text-sm text-ink-soft', q.excerpt);

        // footer
        const footer = el('div', 'mt-3 flex items-center gap-3 text-sm font-semibold text-ink-soft');
        if (q.plant_name) {
            const tag = el('a', 'relative z-10 rounded-md bg-brand-tint px-2.5 py-1 text-xs font-extrabold uppercase tracking-wide text-ink hover:bg-brand-soft-hover', q.plant_name);
            tag.href = q.plant_url;
            footer.append(tag);
        }
        footer.append(el('span', '', q.answer_count > 0
            ? `${q.answer_count} answer${q.answer_count === 1 ? '' : 's'}`
            : 'No answers yet...'));

        content.append(author, h2, excerpt, footer);
        row.append(votes, content);
        article.append(row);
        return article;
    }

    function buildEmptyState(filter, query) {
        const wrap = el('div', 'flex min-h-[374px] items-center justify-center');
        const box = el('div', 'flex w-full max-w-sm flex-col items-center gap-4 rounded-3xl border-2 border-dashed border-ink/30 bg-surface p-6 text-center');
        const iconWrap = el('span', 'flex size-12 items-center justify-center rounded-full bg-brand-tint');
        const icon = el('img');
        icon.alt = '';
        icon.src = query ? '/static/img/icons/search.svg' : '/static/img/icons/x.svg';
        icon.width = 22;
        iconWrap.append(icon);
        box.append(iconWrap);

        const buttonClass = 'rounded-full border-2 border-ink bg-brand px-6 py-3 text-[15px] font-extrabold text-white hover:bg-brand-hover transition duration-150 ease-out active:scale-[0.97]';

        if (query) {
            box.append(
                el('h2', 'font-display text-xl leading-[1.3]', 'No questions found'),
                el('p', 'text-sm text-ink-soft', `No questions match "${query}". Try another word or plant name.`)
            );
            const clear = el('a', buttonClass, 'Clear search');
            clear.href = '?filter=' + encodeURIComponent(filter);
            clear.dataset.filter = filter;
            box.append(clear);
        } else {
            box.append(
                el('h2', 'font-display text-xl leading-[1.3]', 'No questions yet'),
                el('p', 'text-sm text-ink-soft', 'Be the first to ask the community something about your plants.')
            );
        }
        wrap.append(box);
        return wrap;
    }

    function renderCards(questions, filter, query) {
        if (questions.length === 0) {
            cards.replaceChildren(buildEmptyState(filter, query));
            return;
        }
        const grid = el('div', 'grid gap-6');
        questions.forEach((q, i) => {
            const item = el('div', 'h-full transition-opacity duration-400 ease-out delay-(--stagger) starting:opacity-0 motion-reduce:delay-0');
            item.style.setProperty('--stagger', (i < 9 ? i * 40 : 360) + 'ms');
            item.append(buildQuestionCard(q));
            grid.append(item);
        });
        cards.replaceChildren(grid);
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

    // Clicks on a plant in the Popular Plants box: show that plant's questions without a reload.
    // Clicking the plant that's already chosen shows every question again.
    document.addEventListener('click', (event) => {
        const link = event.target.closest('a[data-plant]');
        if (!link || !plantInput || event.ctrlKey || event.metaKey || event.shiftKey) {
            return;
        }
        event.preventDefault();
        clearTimeout(typingTimer);
        const slug = plantInput.value === link.dataset.plant ? '' : link.dataset.plant;
        showPlant(slug);
        loadCards(filterInput.value, searchInput.value.trim(), 'push');
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
        showPlant(params.get('plant') || '');
        loadCards(params.get('filter') || DEFAULT_FILTER, params.get('q') || '', 'none');
    });

    // Lets other scripts (like question_form.js) refresh the list after posting a question:
    //   window.reloadQuestionCards();
    window.reloadQuestionCards = () => {
        const params = new URLSearchParams(window.location.search);
        loadCards(params.get('filter') || DEFAULT_FILTER, params.get('q') || '', 'none');
    };

    // First load: the template renders an empty #question-cards, the API fills it
    const initial = new URLSearchParams(window.location.search);
    showPlant(initial.get('plant') || '');
    loadCards(initial.get('filter') || DEFAULT_FILTER, initial.get('q') || '', 'none');
})();