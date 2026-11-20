const answerForm = document.getElementById('answer-form');
// Guests don't get the answer form, so there is nothing to set up for them.
const ANSWER_QUESTION_ENDPOINT = answerForm ? answerForm.dataset.endpoint : null;

async function createAnswer(event) {
    event.preventDefault();
    const submitButton = answerForm.querySelector('button[type="submit"]');
    submitButton.disabled = true;

    try {
        const response = await fetch(ANSWER_QUESTION_ENDPOINT, {
            method: 'POST',
            headers: {'X-CSRFToken': getCookie('csrftoken')},
            body: new FormData(answerForm)
        });
        const result = await response.json().catch(() => ({}));

        if (!response.ok) {
            showToast('Could not post answer', result.message || 'Please try again.', 'error');
            return;
        }

        showToast('Answer posted', 'Thanks for helpin\' out a fellow gardener!');
        answerForm.reset();
    } catch (error) {
        console.error('Error creating answer:', error);
    } finally {
        submitButton.disabled = false;
        window.reloadAnswerCards();
    }
}

if (answerForm){
    answerForm.addEventListener('submit', createAnswer)
}