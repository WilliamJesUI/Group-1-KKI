// Goal pop-ups ("Start a goal", "Edit goal", "Log progress", "Delete goal").
// The forms are sent with fetch, and errors show under each field without reloading the page.
const goalModal = document.getElementById('goal-modal');
const goalForm = document.getElementById('goal-form');
const logModal = document.getElementById('log-modal');
const logForm = document.getElementById('log-form');
const deleteModal = document.getElementById('delete-goal-modal');
const deleteForm = document.getElementById('delete-goal-form');
const createUrl = goalForm ? goalForm.action : '';

// Remove the red borders and messages from the last attempt
function clearErrors(form) {
    form.querySelectorAll('[data-error-for]').forEach((message) => {
        message.textContent = '';
        message.classList.add('hidden');
    });
    form.querySelectorAll('[aria-invalid]').forEach((input) => input.removeAttribute('aria-invalid'));
}

// Show each error from Django under its field, e.g. { title: [{ message: "Please give your goal a name." }] }
function showErrors(form, errors) {
    for (const [field, fieldErrors] of Object.entries(errors)) {
        const message = form.querySelector(`[data-error-for="${field}"]`) || form.querySelector('[data-error-for="__all__"]');
        if (message) {
            message.textContent = Array.isArray(fieldErrors) 
                ? fieldErrors.map((error) => error.message || error).join(' ')
                : fieldErrors;
            message.classList.remove('hidden');
        }
        const input = form.elements[field];
        if (input) {
            input.setAttribute('aria-invalid', 'true');
        }
    }
}

// Sends a form with fetch. onSuccess(result) returns true when the page is about to reload.
async function sendForm(form, onSuccess) {
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) submitButton.disabled = true;
    clearErrors(form);
    let leavingPage = false;
    try {
        const response = await fetch(form.action, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken'), 'X-Requested-With': 'XMLHttpRequest' }, // getCookie comes from static/js/csrf.js
            body: new FormData(form),
        });
        const result = await response.json().catch(() => ({}));
        if (response.ok) {
            leavingPage = onSuccess(result);
            // Badges, stats and milestones depend on goals, so reload just those parts (refreshRegions is in ajax_forms.js)
            if (!leavingPage && typeof refreshRegions === 'function') refreshRegions(window.location.href);
        } else if (result.errors) {
            showErrors(form, result.errors);
        } else {
            showErrors(form, { __all__: [{ message: result.message || `Something went wrong (status ${response.status}).` }] });
        }
    } catch (error) {
        showErrors(form, { __all__: [{ message: 'Could not reach the server. Please try again.' }] });
    } finally {
        if (!leavingPage) {
            submitButton.disabled = false;
            // Disabling the button sends keyboard focus back to the page, so put it on the first error (or the button)
            (form.querySelector('[aria-invalid="true"]') || submitButton).focus();
        }
    }
}

// Today's date as YYYY-MM-DD in the user's own time zone (toISOString alone would give the UTC date)
function today() {
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    return now.toISOString().slice(0, 10);
}

function openGoalModal(card, editUrl) {
    clearErrors(goalForm);
    goalForm.reset();
    const editing = Boolean(card);
    goalForm.action = editing ? editUrl : createUrl;
    document.getElementById('goal-modal-title').textContent = editing ? 'Edit goal' : 'Start a goal';
    document.getElementById('goal-submit').textContent = editing ? 'Save changes' : 'Start goal';
    if (editing) {
        goalForm.elements['title'].value = card.dataset.title;
        goalForm.elements['plant'].value = card.dataset.plant;
        // Tell the plant picker the value changed, so its search box shows the plant's name
        goalForm.elements['plant'].dispatchEvent(new Event('change', { bubbles: true }));
        goalForm.elements['target'].value = card.dataset.target;
        goalForm.elements['finish_by'].value = card.dataset.finishBy;
        goalForm.elements['reason'].value = card.dataset.reason;
    }
    goalModal.showPopover();
}

function openLogModal(card, logUrl) {
    clearErrors(logForm);
    logForm.reset();
    logForm.action = logUrl;
    logForm.dataset.goalId = card.dataset.goalCard;
    logForm.elements['date'].value = today();
    const done = card.querySelector('[data-done]').textContent;
    document.getElementById('log-subtitle').textContent = `${card.dataset.title} \u00b7 ${done} of ${card.dataset.target} done`;
    logModal.showPopover();
}

function openDeleteModal(card, deleteUrl) {
    clearErrors(deleteForm);
    deleteForm.action = deleteUrl;
    deleteForm.dataset.goalId = card.dataset.goalCard;
    deleteModal.querySelector('[data-delete-title]').textContent = card.dataset.title;
    deleteModal.showPopover();
}

// The progress card changes in place after "Save progress", so the page doesn't reload
function updateCard(goalId, result) {
    const card = document.querySelector(`[data-goal-card="${goalId}"]`);
    if (!card) return;
    card.querySelector('[data-done]').textContent = result.done;
    const bar = card.querySelector('[role="progressbar"]');
    bar.setAttribute('aria-valuenow', result.percent);
    bar.firstElementChild.style.width = `${result.percent}%`;
    if (result.is_complete) {
        card.querySelector('[data-goal-log]').classList.add('hidden');
        card.querySelector('[data-complete-label]').classList.remove('hidden');
    }
}
// Goal text typed by the user goes into innerHTML below, so turn < > & " ' into safe characters first
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text ?? '';
    return div.innerHTML.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function renderOrUpdateGoalCard(goal) {
    let card = document.querySelector(`[data-goal-card="${goal.id}"]`);

    if (card) {
        // UPDATE Card
        card.dataset.title = goal.title;
        card.dataset.plant = goal.plant_id;
        card.dataset.target = goal.target;
        card.dataset.finishBy = goal.finish_by;
        card.dataset.reason = goal.reason;

        card.querySelector('h3').textContent = goal.title;
        card.querySelector('h3 + p').textContent = goal.plant_name + (goal.finish_by_formatted ? ' \u00b7 Finish by ' + goal.finish_by_formatted : '');
        card.querySelector('[data-done]').textContent = goal.done;
        
        const bar = card.querySelector('[role="progressbar"]');
        if (bar) {
            bar.setAttribute('aria-valuenow', goal.percent);
            bar.firstElementChild.style.width = `${goal.percent}%`;
        }
    } else {
        // CREATE Card
        const emptyState = document.querySelector('#goals .border-dashed')?.closest('.lg\\:col-span-2');
        if (emptyState) emptyState.remove();

        const grid = document.querySelector('#goals .grid');
        const article = document.createElement('article');
        article.setAttribute('data-goal-card', goal.id);
        article.setAttribute('data-title', goal.title);
        article.setAttribute('data-plant', goal.plant_id);
        article.setAttribute('data-target', goal.target);
        article.setAttribute('data-finish-by', goal.finish_by);
        article.setAttribute('data-reason', goal.reason);
        article.className = 'flex flex-col gap-3 rounded-2xl border-2 border-ink bg-surface p-[18px]';

        article.innerHTML = `
            <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                    <h3 class="font-display text-xl leading-tight">${escapeHtml(goal.title)}</h3>
                    <p class="text-xs text-ink-soft">${escapeHtml(goal.plant_name)}${goal.finish_by_formatted ? ' &middot; Finish by ' + goal.finish_by_formatted : ''}</p>
                </div>
                <span data-complete-label class="${!goal.is_complete ? 'hidden ' : ''}shrink-0 rounded-full bg-brand-soft px-3 py-1 text-[11px] font-black uppercase tracking-[0.08em]">Complete</span>
            </div>
            ${goal.reason ? `<p class="text-sm text-ink-soft">${escapeHtml(goal.reason)}</p>` : ''}
            <div>
                <div class="h-2 rounded-full bg-brand-tint" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${goal.percent}" aria-label="${escapeHtml(goal.title)} progress">
                    <div class="h-full rounded-full bg-brand" style="width: ${goal.percent}%"></div>
                </div>
                <p class="mt-1.5 text-xs text-ink-soft"><span data-done>${goal.done}</span> of ${goal.target} done</p>
            </div>
            <div class="flex flex-wrap gap-2">
                <button type="button" data-goal-log data-url="/achievements/goals/${goal.id}/log/" class="${goal.is_complete ? 'hidden ' : ''}rounded-full border-2 border-ink bg-brand px-4 py-2 text-[13px] font-extrabold text-white hover:bg-brand-hover">Log progress</button>
                <button type="button" data-goal-edit data-url="/achievements/goals/${goal.id}/edit/" class="rounded-full border-2 border-ink bg-surface px-4 py-2 text-[13px] font-extrabold hover:bg-brand-tint">Edit</button>
                <button type="button" data-goal-delete data-url="/achievements/goals/${goal.id}/delete/" class="rounded-full border-2 border-ink bg-surface px-4 py-2 text-[13px] font-extrabold hover:bg-pink">Delete</button>
            </div>
        `;
        grid.appendChild(article);
        document.querySelector('[data-goal-new-header]')?.classList.remove('hidden');
    }
}

if (goalForm) {
    document.addEventListener('click', (event) => {
        const button = event.target.closest('[data-goal-new], [data-goal-edit], [data-goal-log], [data-goal-delete]');
        if (!button) {
            return;
        }
        const card = button.closest('[data-goal-card]');
        if (button.hasAttribute('data-goal-new')) {
            openGoalModal(null, '');
        } else if (button.hasAttribute('data-goal-edit')) {
            openGoalModal(card, button.dataset.url);
        } else if (button.hasAttribute('data-goal-log')) {
            openLogModal(card, button.dataset.url);
        } else {
            openDeleteModal(card, button.dataset.url);
        }
    });

    // Start and edit: the card is added or updated in place, no reload
    goalForm.addEventListener('submit', (event) => {
        event.preventDefault();
        sendForm(goalForm, (result) => {
            if (result.goal) renderOrUpdateGoalCard(result.goal);
            goalModal.hidePopover();
            if (result.message && typeof showToast === 'function') {
                const parts = result.message.split('\n');
                showToast(parts[0], parts[1] || '', 'success');
            }
            return false;
        });
    });

    logForm.addEventListener('submit', (event) => {
        event.preventDefault();
        sendForm(logForm, (result) => {
            updateCard(logForm.dataset.goalId, result);
            logModal.hidePopover();
            if (typeof showToast === 'function') {
                showToast(result.title, result.message, 'success');
            }
            return false;
        });
    });
    deleteForm.addEventListener('submit', (event) => {
        event.preventDefault();
        sendForm(deleteForm, (result) => {
            const goalId = deleteForm.dataset.goalId || result.goal_id;
            const card = document.querySelector(`[data-goal-card="${goalId}"]`);
            if (card) {
                card.remove();
            }
            deleteModal.hidePopover();
            if (result.message && typeof showToast === 'function') {
                const parts = result.message.split('\n');
                showToast(parts[0], parts[1] || '', 'success');
            }
            return false;
        });
    });

    // Open the browser's date picker when the field is clicked
    document.querySelectorAll('#goal-form input[type="date"], #log-form input[type="date"]').forEach((input) => {
        input.addEventListener('click', () => input.showPicker?.());
    });

    // Pressing Back after saving can bring this page back with the button still disabled
    window.addEventListener('pageshow', (event) => {
        if (event.persisted) {
            document.querySelectorAll('#goal-form button[type="submit"], #log-form button[type="submit"]').forEach((button) => {
                button.disabled = false;
            });
        }
    });
}