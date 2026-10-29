(() => {
    function errorTitle(status, fallback) {
        if (status === 403) return 'Not allowed';
        if (status === 404) return 'Not found';
        return fallback;
    }

    // Swap between the normal view and the inline edit form
    function setEditing(card, editing) {
        card.querySelector('[data-answer-body]').hidden = editing;
        card.querySelector('[data-edit-form]').hidden = !editing;
        card.querySelector('[data-answer-actions]').hidden = editing;
        if (editing) card.querySelector('[data-edit-form] textarea').focus();
    }

    document.addEventListener('click', async (event) => {
        const card = event.target.closest('[data-answer-card]');
        if (!card) return;

        if (event.target.closest('[data-edit-answer]')) {
            setEditing(card, true);
            return;
        }

        if (event.target.closest('[data-cancel-edit]')) {
            const textarea = card.querySelector('[data-edit-form] textarea');
            textarea.value = textarea.defaultValue; // throw away unsaved changes
            setEditing(card, false);
            return;
        }

        const deleteBtn = event.target.closest('[data-delete-answer]');
        if (deleteBtn) {
            if (!await confirmDelete({ title: 'Delete this answer?', message: "This can't be undone." })) return;
            deleteBtn.disabled = true;
            try {
                const response = await fetch(deleteBtn.dataset.endpoint, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': getCookie('csrftoken') },
                });
                const result = await response.json().catch(() => ({}));

                if (!response.ok) {
                    showToast(errorTitle(response.status, 'Could not delete'),
                              result.message || 'Please try again.', 'error');
                    deleteBtn.disabled = false;
                    return;
                }

                showToast('Answer deleted', 'It has been removed.');
                if (window.reloadAnswerCards) window.reloadAnswerCards();
            } catch (error) {
                console.error('Error deleting answer:', error);
                showToast('Network error', 'Please check your connection and try again.', 'error');
                deleteBtn.disabled = false;
            }
        }
    });

    document.addEventListener('submit', async (event) => {
        const form = event.target.closest('[data-edit-form]');
        if (!form) return;
        event.preventDefault();

        const submitButton = form.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        try {
            const response = await fetch(form.dataset.endpoint, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') },
                body: new FormData(form),
            });
            const result = await response.json().catch(() => ({}));

            if (!response.ok) {
                showToast(errorTitle(response.status, 'Could not save'),
                          result.message || 'Please try again.', 'error');
                return; // form stays open so the user keeps their edits
            }

            showToast('Answer updated', 'Your changes are saved.');
            if (window.reloadAnswerCards) window.reloadAnswerCards();
        } catch (error) {
            console.error('Error updating answer:', error);
            showToast('Network error', 'Please check your connection and try again.', 'error');
        } finally {
            submitButton.disabled = false;
        }
    });
})();