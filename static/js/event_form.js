// "Host an event" pop-up: sends the form with fetch and shows errors without reloading the page
const hostEventForm = document.getElementById('host-event-form');

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
    let leavingPage = false;

    try {
        const response = await fetch(hostEventForm.action, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') }, // getCookie comes from static/js/csrf.js
            body: new FormData(hostEventForm),
        });
        const result = await response.json().catch(() => ({}));

        if (response.ok) {
            // Go to the new event's page. The button stays disabled while it loads,
            // so a second click can't save the event twice.
            leavingPage = true;
            window.location.href = result.url;
        } else if (result.errors) {
            showErrors(result.errors);
        } else {
            showErrors({ __all__: [{ message: result.message || `Something went wrong (status ${response.status}).` }] });
        }
    } catch (error) {
        showErrors({ __all__: [{ message: 'Could not reach the server. Please try again.' }] });
    } finally {
        if (!leavingPage) {
            submitButton.disabled = false;
        }
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

// When editing, the event may already have a photo. We remember it so we can show it again.
let currentCover = null;

function showEmptyBox() {
    const dropBox = document.getElementById('cover-drop');
    const preview = document.getElementById('cover-preview');
    dropBox.classList.remove('hidden');
    dropBox.classList.add('flex');
    preview.classList.add('hidden');
    preview.classList.remove('flex');
}

function showPreview(src, name) {
    const dropBox = document.getElementById('cover-drop');
    const preview = document.getElementById('cover-preview');
    const previewImg = document.getElementById('cover-preview-img');
    if (previewImg.src.startsWith('blob:')) {
        URL.revokeObjectURL(previewImg.src); // free the old temporary link
    }
    previewImg.src = src;
    document.getElementById('cover-file-name').textContent = name;
    dropBox.classList.add('hidden');
    dropBox.classList.remove('flex');
    preview.classList.remove('hidden');
    preview.classList.add('flex');
}

// Forget the picked file and go back to the current photo (if there is one and it wasn't removed)
function resetCover() {
    hostEventForm.elements['cover_upload'].value = '';
    const removed = hostEventForm.elements['remove_cover'].value === 'True';
    if (currentCover && !removed) {
        showPreview(currentCover, 'Current photo');
    } else {
        showEmptyBox();
    }
}

// "Remove" button: no photo at all. When editing, this also tells the server to delete the current photo.
function removeCover() {
    setCoverError('');
    hostEventForm.elements['cover_upload'].value = '';
    hostEventForm.elements['remove_cover'].value = currentCover ? 'True' : '';
    showEmptyBox();
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
    // A new photo replaces the current one, so there's nothing to remove
    hostEventForm.elements['remove_cover'].value = '';
    showPreview(URL.createObjectURL(file), file.name); // a temporary link to the file on this computer
}

function setUpCoverBox() {
    const coverInput = hostEventForm.elements['cover_upload'];
    const dropBox = document.getElementById('cover-drop');
    const dropText = document.getElementById('cover-drop-text');

    // If the page opened with a photo already in the preview, that's the event's current photo
    const previewSrc = document.getElementById('cover-preview-img').getAttribute('src');
    currentCover = previewSrc ? previewSrc : null;

    coverInput.addEventListener('change', () => showCover(coverInput.files[0]));
    document.getElementById('cover-remove').addEventListener('click', removeCover);

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

    // Pressing Back after saving can bring this page back exactly as it was left (persisted = true),
    // with the button still disabled. Turn it back on so the form works again.
    window.addEventListener('pageshow', (event) => {
        if (event.persisted) {
            hostEventForm.querySelector('button[type="submit"]').disabled = false;
        }
    });

    // Open the browser's date and time picker when the field is clicked
    hostEventForm.querySelectorAll('input[type="date"], input[type="time"]').forEach((input) => {
        input.addEventListener('click', () => input.showPicker?.());
    });
}
