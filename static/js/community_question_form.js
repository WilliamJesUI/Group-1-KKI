const questionForm = document.getElementById('question-form');
const CREATE_QUESTION_ENDPOINT = questionForm.dataset.endpoint;

async function createQuestion(event) {
    event.preventDefault();

    const submitButton = questionForm.querySelector('button[type="submit"]');
    submitButton.disabled = true;

    try {
            const response = await fetch(CREATE_QUESTION_ENDPOINT, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') },
                body: new FormData(questionForm),
            });
            const result = await response.json().catch(() => ({}));

            if (!response.ok) {
                showToast('Could not post question', result.message || 'Please try again.', 'error');
                return;
            }

            showToast('Question posted', 'It is now live in the community.');
            questionForm.reset();
            if (window.reloadQuestionCards) {
                window.reloadQuestionCards();
            }
    } catch (error) {
        console.error('Error creating question:', error);
    } finally {
        submitButton.disabled = false;
        window.reloadQuestionCards();
        document.getElementById('ask-question-modal').hidePopover();
    }
}

if (questionForm){
    questionForm.addEventListener('submit', createQuestion);
}

