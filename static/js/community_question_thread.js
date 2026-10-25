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
