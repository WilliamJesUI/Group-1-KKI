// "Host an event" pop-up: sends the form with fetch and shows errors without reloading the page
const hostEventForm = document.getElementById('host-event-form');

// Read a cookie value, used to get the CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Remove the red borders and messages from the last attempt
function clearErrors() {
    hostEventForm.querySelectorAll('[data-error-for]').forEach((message) => {
        message.textContent = '';
        message.classList.add('hidden');
    });
    hostEventForm.querySelectorAll('[aria-invalid]').forEach((input) => {
        input.removeAttribute('aria-invalid');
    });
}

// Show each error from Django under its field, e.g. { name: [{ message: "Please give your event a name." }] }
function showErrors(errors) {
    for (const [field, fieldErrors] of Object.entries(errors)) {
        const message = hostEventForm.querySelector(`[data-error-for="${field}"]`)
            || hostEventForm.querySelector('[data-error-for="__all__"]');
        message.textContent = fieldErrors.map((error) => error.message).join(' ');
        message.classList.remove('hidden');

        const input = hostEventForm.elements[field];
        if (input) {
            input.setAttribute('aria-invalid', 'true');
        }
    }
}

async function publishEvent(event) {
    event.preventDefault();
    const submitButton = hostEventForm.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    clearErrors();

    try {
        const response = await fetch(hostEventForm.action, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            body: new FormData(hostEventForm),
        });
        const result = await response.json().catch(() => ({}));

        if (response.ok) {
            // Go to the new event's page
            window.location.href = result.url;
        } else if (result.errors) {
            showErrors(result.errors);
        } else {
            showErrors({ __all__: [{ message: result.message || `Something went wrong (status ${response.status}).` }] });
        }
    } catch (error) {
        showErrors({ __all__: [{ message: 'Could not reach the server. Please try again.' }] });
    } finally {
        submitButton.disabled = false;
    }
}

// Cover photo box: pick or drop a photo, show a preview, or remove it again
const ALLOWED_COVER_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_COVER_SIZE = 2 * 1024 * 1024; // 2 MB, same limit as the server

function setCoverError(text) {
    const message = hostEventForm.querySelector('[data-error-for="cover_upload"]');
    message.textContent = text;
    message.classList.toggle('hidden', !text);
    // Red border on the drop box while there's an error
    const coverInput = hostEventForm.elements['cover_upload'];
    if (text) {
        coverInput.setAttribute('aria-invalid', 'true');
    } else {
        coverInput.removeAttribute('aria-invalid');
    }
}

function resetCover() {
    const coverInput = hostEventForm.elements['cover_upload'];
    coverInput.value = '';
    URL.revokeObjectURL(document.getElementById('cover-preview-img').src);
    document.getElementById('cover-drop').classList.remove('hidden');
    document.getElementById('cover-preview').classList.add('hidden');
    document.getElementById('cover-preview').classList.remove('flex');
}

function showCover(file) {
    setCoverError('');
    if (!file) {
        resetCover();
        return;
    }
    // Quick check so people don't wait for the server. The server checks again for real.
    if (!ALLOWED_COVER_TYPES.includes(file.type)) {
        resetCover();
        setCoverError('Please pick a JPG, PNG or WebP photo.');
        return;
    }
    if (file.size > MAX_COVER_SIZE) {
        resetCover();
        setCoverError('That photo is too big. Please pick one under 2 MB.');
        return;
    }
    const previewImg = document.getElementById('cover-preview-img');
    URL.revokeObjectURL(previewImg.src);
    previewImg.src = URL.createObjectURL(file); // a temporary link to the file on this computer
    document.getElementById('cover-file-name').textContent = file.name;
    document.getElementById('cover-drop').classList.add('hidden');
    document.getElementById('cover-preview').classList.remove('hidden');
    document.getElementById('cover-preview').classList.add('flex');
}

function setUpCoverBox() {
    const coverInput = hostEventForm.elements['cover_upload'];
    const dropBox = document.getElementById('cover-drop');
    const dropText = document.getElementById('cover-drop-text');

    coverInput.addEventListener('change', () => showCover(coverInput.files[0]));
    document.getElementById('cover-remove').addEventListener('click', resetCover);

    dropBox.addEventListener('dragover', (event) => {
        event.preventDefault(); // needed, otherwise the browser opens the photo in the tab
        dropBox.dataset.drag = '';
        dropText.textContent = 'Drop to upload';
    });
    dropBox.addEventListener('dragleave', () => {
        delete dropBox.dataset.drag;
        dropText.textContent = 'Drop a photo or browse';
    });
    dropBox.addEventListener('drop', (event) => {
        event.preventDefault();
        delete dropBox.dataset.drag;
        dropText.textContent = 'Drop a photo or browse';
        const file = event.dataTransfer.files[0];
        if (!file) {
            return;
        }
        // Put only the first dropped file into the real file input, so it gets sent with the form
        const transfer = new DataTransfer();
        transfer.items.add(file);
        coverInput.files = transfer.files;
        showCover(file);
    });
}

if (hostEventForm) {
    hostEventForm.addEventListener('submit', publishEvent);
    setUpCoverBox();

    // Open the browser's date and time picker when the field is clicked
    hostEventForm.querySelectorAll('input[type="date"], input[type="time"]').forEach((input) => {
        input.addEventListener('click', () => input.showPicker?.());
    });
}
