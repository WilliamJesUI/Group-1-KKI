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
            document.getElementById('ask-question-modal').hidePopover();

            // Only count it once the server said it worked
            const countCard = document.getElementById('questions-asked-card');
            countCard.textContent = Number(countCard.textContent) + 1;
            if (window.reloadQuestionCards) {
                window.reloadQuestionCards();
                if (window.refreshPopularPlants) {
                    window.refreshPopularPlants();
                }
            }
    } catch (error) {
        console.error('Error creating question:', error);
        showToast('Network error', 'Please check your connection and try again.', 'error');
    } finally {
        submitButton.disabled = false;
    }
}

if (questionForm){
    questionForm.addEventListener('submit', createQuestion);
}

