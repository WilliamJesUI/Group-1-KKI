document.addEventListener('DOMContentLoaded', () => {
    const extraFields = document.getElementById('extra-fields');
    const toggleBtns = document.querySelectorAll('.toggle-extra-fields');
    
    toggleBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            extraFields.classList.toggle('hidden');
            extraFields.classList.toggle('flex');
        });
    });

    const form = document.getElementById('create-post-form');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = form.querySelector('button[type="submit"]');
            btn.disabled = true;
            btn.textContent = 'Posting...';

            try {
                const res = await fetch(form.action, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': getCookie('csrftoken') },
                    body: new FormData(form)
                });
                if (res.ok) {
                    showToast('Success', 'Your post is blooming!');
                    setTimeout(() => window.location.reload(), 1000);
                } else {
                    const data = await res.json();
                    showToast('Error', 'Could not post. Please check your text.', 'error');
                    btn.disabled = false;
                    btn.textContent = 'Post';
                }
            } catch (err) {
                showToast('Error', 'Network error.', 'error');
                btn.disabled = false;
                btn.textContent = 'Post';
            }
        });
    }

    document.querySelectorAll('.like-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const url = btn.dataset.url;
            try {
                const res = await fetch(url, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': getCookie('csrftoken') }
                });
                const data = await res.json();
                if (data.status === 'success') {
                    btn.querySelector('.like-count').textContent = data.like_count;
                    const svg = btn.querySelector('svg');
                    if (data.liked) {
                        btn.classList.add('text-danger');
                        btn.classList.remove('text-ink');
                        svg.setAttribute('fill', 'currentColor');
                    } else {
                        btn.classList.remove('text-danger');
                        btn.classList.add('text-ink');
                        svg.setAttribute('fill', 'none');
                    }
                }
            } catch (err) {
                console.error(err);
            }
        });
    });
});