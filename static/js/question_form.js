const questionForm = document.getElementById('question-form');
const CREATE_QUESTION_ENDPOINT = questionForm.dataset.endpoint;
console.log(CREATE_QUESTION_ENDPOINT);

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
    } catch (error) {
        console.error('Error creating question:', error);
    } finally {
        submitButton.disabled = false;
    }
}

if (questionForm){
    questionForm.addEventListener('submit', createQuestion);
}

