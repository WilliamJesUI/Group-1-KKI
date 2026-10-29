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
        message.textContent = fieldErrors.map((error) => error.message).join(' ');
        message.classList.remove('hidden');
        const input = form.elements[field];
        if (input) {
            input.setAttribute('aria-invalid', 'true');
        }
    }
}

// Sends a form with fetch. onSuccess(result) returns true when the page is about to reload.
async function sendForm(form, onSuccess) {
    const submitButton = form.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    clearErrors(form);
    let leavingPage = false;
    try {
        const response = await fetch(form.action, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') }, // getCookie comes from static/js/csrf.js
            body: new FormData(form),
        });
        const result = await response.json().catch(() => ({}));
        if (response.ok) {
            leavingPage = onSuccess(result);
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
    deleteForm.action = deleteUrl;
    deleteModal.querySelector('[data-delete-title]').textContent = card.dataset.title;
    deleteModal.showPopover();
}

// The progress card changes in place after "Save progress", so the page doesn't reload
function updateCard(goalId, result) {
    const card = document.querySelector(`[data-goal-card="${goalId}"]`);
    card.querySelector('[data-done]').textContent = result.done;
    const bar = card.querySelector('[role="progressbar"]');
    bar.setAttribute('aria-valuenow', result.percent);
    bar.firstElementChild.style.width = `${result.percent}%`;
    if (result.is_complete) {
        card.querySelector('[data-goal-log]').classList.add('hidden');
        card.querySelector('[data-complete-label]').classList.remove('hidden');
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

    // Start and edit: reload so the new list shows, the toast comes from the server (Django messages)
    goalForm.addEventListener('submit', (event) => {
        event.preventDefault();
        sendForm(goalForm, () => {
            window.location.reload();
            return true;
        });
    });

    logForm.addEventListener('submit', (event) => {
        event.preventDefault();
        sendForm(logForm, (result) => {
            updateCard(logForm.dataset.goalId, result);
            logModal.hidePopover();
            showToast(result.title, result.message, 'success'); // showToast comes from static/js/toast.js
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