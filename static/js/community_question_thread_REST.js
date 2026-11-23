// Vote handler: delegated on document, so it also works on cards rendered by JS
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
            const fallback = response.status === 403 ? 'Please log in first.' : 'Please try again.';
            showToast(title, data.message || fallback, 'error');
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

    // Set by the template: data-api-url="{% url 'community:answer-list' question.id %}"
    const API_URL = cards.dataset.apiUrl;
    const DEFAULT_FILTER = 'most_helpful';   // must match the view's default
    let latestAnswerRequest = 0;

    // ---------- helpers ----------

    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    // Static, trusted SVG markup only (never put user text in here)
    function icon(markup) {
        const t = document.createElement('template');
        t.innerHTML = markup.trim();
        return t.content.firstChild;
    }

    const ARROW = '<svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7"/></svg>';
    const HEART = '<svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1.1L12 21l7.8-7.5 1-1.1a5.5 5.5 0 0 0 0-7.8z"/></svg>';

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

    // Updates the "N answers" labels and hides the owner's edit/delete box once answered
    function updateCounts(n) {
        document.querySelectorAll('[data-answer-count-label]').forEach((label) => {
            label.textContent = n === 0
                ? (label.dataset.emptyText || 'No answers yet')
                : `${n} answer${n === 1 ? '' : 's'}`;
        });
        const ownerBox = document.getElementById('question_edit_delete_card');
        if (ownerBox) ownerBox.hidden = n > 0;
    }

    function currentFilter() {
        return new URLSearchParams(window.location.search).get('filter') || DEFAULT_FILTER;
    }

    // ---------- rendering ----------

    function buildAnswerCard(a, isTop) {
        const article = el('article', 'mb-5 rounded-2xl border-2 border-ink p-5 ' + (isTop ? 'bg-brand-tint' : 'bg-white'));
        article.dataset.answerCard = '';
        const row = el('div', 'flex gap-4');

        // vote box
        const votes = el('div', 'flex w-[64px] shrink-0 flex-col items-center self-start rounded-xl border-2 border-ink bg-brand-tint px-2 py-3 text-center');
        const count = el('span', 'text-sm font-extrabold', String(a.vote_count));
        count.dataset.count = '';
        votes.append(icon(ARROW), count, el('span', 'text-xs text-ink-soft', 'votes'));

        const content = el('div', 'min-w-0 flex-1');

        // author row
        const author = el('a', 'flex w-fit flex-wrap items-center gap-2 text-sm transition-transform duration-150 hover:scale-102');
        author.href = a.author_url;
        let avatar;
        if (a.author_picture) {
            avatar = el('span', 'card-avatar relative overflow-hidden !p-0');
            const img = el('img', 'absolute inset-0 m-0 size-full max-w-none object-cover');
            img.src = a.author_picture;
            img.alt = 'Profile picture of ' + a.author_name;
            avatar.append(img);
        } else {
            avatar = el('span', 'card-avatar ' + (a.author_avatar_class || ''), a.author_initials);
        }
        author.append(
            avatar,
            el('span', 'font-semibold', a.author_name),
            el('span', 'text-ink-soft', '· ' + a.time_ago)
        );
        if (isTop) {
            author.append(el('span', 'rounded-full border-2 border-ink bg-green-200 px-3 py-0.5 text-xs font-extrabold uppercase tracking-wider text-green-900', 'Top answer'));
        }

        // body
        const body = el('p', 'mt-2 whitespace-pre-line text-[15px] leading-relaxed', a.body);
        body.dataset.answerBody = '';
        content.append(author, body);

        // inline edit form (author only)
        if (a.can_edit) {
            const form = el('form', 'mt-2');
            form.dataset.editForm = '';
            form.dataset.endpoint = a.url;
            form.hidden = true;
            const textarea = el('textarea', 'w-full resize-none rounded-3xl border-2 border-ink bg-white px-4 py-3 text-[15px] focus:outline-none focus:ring-2 focus:ring-green-800');
            textarea.name = 'body';
            textarea.rows = 4;
            textarea.required = true;
            textarea.value = a.body;
            const buttons = el('div', 'mt-2 flex justify-end gap-2');
            const cancel = el('button', 'rounded-full border-2 border-ink bg-surface px-4 py-1.5 text-sm font-bold hover:bg-brand-tint', 'Cancel');
            cancel.type = 'button';
            cancel.dataset.cancelEdit = '';
            const save = el('button', 'rounded-full border-2 border-ink bg-brand px-4 py-1.5 text-sm font-bold text-white hover:bg-brand-hover disabled:opacity-40', 'Save');
            save.type = 'submit';
            buttons.append(cancel, save);
            form.append(textarea, buttons);
            content.append(form);
        }

        // actions
        const actions = el('div', 'mt-3 flex flex-wrap items-center gap-4');
        actions.dataset.answerActions = '';

        const helpful = el('button', 'inline-flex items-center gap-2 text-sm font-bold hover:text-brand aria-pressed:text-brand [&[aria-pressed=true]_svg]:fill-current');
        helpful.type = 'button';
        helpful.dataset.voteUrl = a.vote_url;
        helpful.setAttribute('aria-pressed', String(a.is_voted));
        helpful.append(icon(HEART), document.createTextNode('Helpful'));
        actions.append(helpful);

        if (a.can_edit) {
            const edit = el('button', 'text-sm font-bold hover:text-brand', 'Edit');
            edit.type = 'button';
            edit.dataset.editAnswer = '';
            actions.append(edit);
        }
        if (a.can_delete) {
            const del = el('button', 'text-sm font-bold text-red-600 hover:text-red-700 disabled:opacity-40', 'Delete');
            del.type = 'button';
            del.dataset.deleteAnswer = '';
            del.dataset.endpoint = a.url;
            actions.append(del);
        }

        content.append(actions);
        row.append(votes, content);
        article.append(row);
        return article;
    }

    function buildEmptyState() {
        return el('p', 'text-ink-soft', 'No answers yet.');
    }

    function renderCards(answers, filter) {
        if (answers.length === 0) {
            cards.replaceChildren(buildEmptyState());
            return;
        }
        const list = el('div');
        answers.forEach((a, i) => {
            // Adjust if your old view used a different rule for "Top answer"
            const isTop = filter === 'most_helpful' && i === 0 && a.vote_count > 0;
            list.append(buildAnswerCard(a, isTop));
        });
        cards.replaceChildren(list);
    }

    // ---------- loading ----------

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
            const response = await fetch(API_URL + url, {
                headers: { 'Accept': 'application/json' },
            });
            if (!response.ok) {
                throw new Error(`status ${response.status}`);
            }
            const answers = await response.json();
            if (requestId === latestAnswerRequest) {
                renderCards(answers, filter);
                // "Mine" only returns your answers, so it can't give the real total
                if (filter !== 'mine') updateCounts(answers.length);
            }
        } catch (error) {
            console.error('Error loading answers:', error);
            if (requestId === latestAnswerRequest) {
                cards.replaceChildren(el('p', 'text-sm text-ink-soft', 'Could not load answers. Please try again.'));
            }
        } finally {
            if (requestId === latestAnswerRequest) {
                cards.removeAttribute('aria-busy');
            }
        }
    }

    // ---------- edit / delete (REST) ----------

    function apiRequest(url, method, body) {
        const headers = {
            'X-CSRFToken': getCookie('csrftoken'),
            'Accept': 'application/json',
        };
        if (body) headers['Content-Type'] = 'application/json';
        return fetch(url, {
            method,
            headers,
            body: body ? JSON.stringify(body) : undefined,
        });
    }

    // Show the edit form
    document.addEventListener('click', (event) => {
        const editBtn = event.target.closest('[data-edit-answer]');
        if (!editBtn) return;
        const card = editBtn.closest('[data-answer-card]');
        card.querySelector('[data-answer-body]').hidden = true;
        const form = card.querySelector('[data-edit-form]');
        form.hidden = false;
        form.querySelector('textarea').focus();
    });

    // Cancel editing
    document.addEventListener('click', (event) => {
        const cancelBtn = event.target.closest('[data-cancel-edit]');
        if (!cancelBtn) return;
        const card = cancelBtn.closest('[data-answer-card]');
        const form = card.querySelector('[data-edit-form]');
        const body = card.querySelector('[data-answer-body]');
        form.querySelector('textarea').value = body.textContent;   // discard changes
        form.hidden = true;
        body.hidden = false;
    });

    // Save: PATCH
    document.addEventListener('submit', async (event) => {
        const form = event.target.closest('[data-edit-form]');
        if (!form) return;
        event.preventDefault();

        const saveBtn = form.querySelector('button[type="submit"]');
        saveBtn.disabled = true;
        try {
            const response = await apiRequest(
                form.dataset.endpoint,
                'PATCH',
                { body: form.querySelector('textarea').value }
            );
            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                const message = (data.body && data.body[0]) || data.detail || 'Please try again.';
                showToast('Could not save', message, 'error');
                return;
            }

            const card = form.closest('[data-answer-card]');
            const body = card.querySelector('[data-answer-body]');
            body.textContent = data.body;                       // server's cleaned version
            form.querySelector('textarea').value = data.body;
            form.hidden = true;
            body.hidden = false;
        } catch (error) {
            console.error('Error updating answer:', error);
            showToast('Network error', 'Please try again.', 'error');
        } finally {
            saveBtn.disabled = false;
        }
    });

    // Delete: DELETE
    document.addEventListener('click', async (event) => {
        const delBtn = event.target.closest('[data-delete-answer]');
        if (!delBtn || delBtn.disabled) return;
    
        delBtn.disabled = true;
        try {
            const response = await apiRequest(delBtn.dataset.endpoint, 'DELETE');
            if (response.status !== 204) {
                const data = await response.json().catch(() => ({}));
                showToast('Could not delete', data.detail || 'Please try again.', 'error');
                return;
            }
            // Re-fetch so the counts and "Top answer" stay correct
            await window.reloadAnswerCards();
        } catch (error) {
            console.error('Error deleting answer:', error);
            showToast('Network error', 'Please try again.', 'error');
        } finally {
            delBtn.disabled = false;   // harmless if the card is already gone
        }
    });

    // ---------- events ----------

    document.addEventListener('click', (event) => {
        const link = event.target.closest('#answer-filter-pills [data-filter]');
        if (!link || event.ctrlKey || event.metaKey || event.shiftKey) return;
        event.preventDefault();
        loadAnswerCards(link.dataset.filter, 'push');
    });

    window.addEventListener('popstate', () => {
        loadAnswerCards(currentFilter(), 'none');
    });

    // Other scripts can call this to refresh the list (e.g. after posting an answer)
    window.reloadAnswerCards = () => loadAnswerCards(currentFilter(), 'none');

    // First load: the template renders an empty #answer-cards, the API fills it
    window.reloadAnswerCards();
})();