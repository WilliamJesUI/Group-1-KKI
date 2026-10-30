/* The landing page at "/" (home/templates/home/landing.html).
   1. Headline lines slide up when the page is ready.
   2. Parts fade up as they scroll into view ([data-rise], [data-plate]).
   3. The big numbers next to "In this issue" count up once.
   4. The plant shelf: pills swap plants without reloading, arrows and a progress bar move the shelf.
   If the visitor turned on reduced motion, 1 to 3 are skipped and everything just shows. */
(function () {
    var calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var root = document.documentElement;

    // 1. Headline
    requestAnimationFrame(function () { root.classList.add('landing-ready'); });

    // 2. Fade up on scroll
    var parts = document.querySelectorAll('[data-rise], [data-plate]');
    if (calm || !('IntersectionObserver' in window)) {
        parts.forEach(function (part) { part.classList.add('is-in'); });
    } else {
        var watcher = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) return;
                entry.target.classList.add('is-in');
                watcher.unobserve(entry.target);
            });
        }, { rootMargin: '0px 0px -10% 0px' });
        parts.forEach(function (part) { watcher.observe(part); });
    }

    // 3. Count up (the real number is already in the HTML, so without JavaScript it is still right)
    if (!calm && 'IntersectionObserver' in window) {
        var counters = document.querySelectorAll('[data-count]');
        var counterWatcher = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) return;
                counterWatcher.unobserve(entry.target);
                countUp(entry.target, parseInt(entry.target.dataset.count, 10) || 0);
            });
        });
        counters.forEach(function (counter) { counterWatcher.observe(counter); });
    }

    function countUp(element, target) {
        var start = performance.now();
        var length = 900;
        function step(now) {
            var done = Math.min((now - start) / length, 1);
            var eased = 1 - Math.pow(1 - done, 3);
            element.textContent = Math.round(target * eased);
            if (done < 1) requestAnimationFrame(step);
        }
        element.textContent = '0';
        requestAnimationFrame(step);
    }

    // 4. Plant shelf
    var shelf = document.querySelector('[data-shelf]');
    if (!shelf) return;
    var content = shelf.querySelector('[data-shelf-content]');
    var progress = shelf.querySelector('[data-shelf-progress]');
    var status = shelf.querySelector('[data-shelf-status]');

    function track() { return content.querySelector('[data-shelf-track]'); }

    function updateProgress() {
        var list = track();
        if (!list || !progress) return;
        var room = list.scrollWidth - list.clientWidth;
        var seen = room > 0 ? (list.scrollLeft + list.clientWidth) / list.scrollWidth : 1;
        progress.style.width = Math.round(seen * 100) + '%';
    }

    function watchTrack() {
        var list = track();
        if (list) list.addEventListener('scroll', updateProgress, { passive: true });
        updateProgress();
    }

    shelf.querySelectorAll('[data-shelf-move]').forEach(function (button) {
        button.addEventListener('click', function () {
            var list = track();
            if (!list) return;
            var direction = parseInt(button.dataset.shelfMove, 10);
            list.scrollBy({ left: direction * list.clientWidth * 0.8, behavior: calm ? 'auto' : 'smooth' });
        });
    });

    // Pills are normal links (?shelf=herbs), so they work without JavaScript too. With it, only the shelf changes.
    content.addEventListener('click', function (event) {
        var pill = event.target.closest('[data-shelf-pill]');
        if (!pill || event.metaKey || event.ctrlKey || event.shiftKey) return;
        event.preventDefault();
        var value = pill.dataset.shelfPill;
        var url = shelf.dataset.shelfUrl + '?shelf=' + encodeURIComponent(value);
        content.setAttribute('aria-busy', 'true');
        fetch(url + '&partial=1', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(function (response) {
                if (!response.ok) throw new Error('Server said ' + response.status);
                return response.text();
            })
            .then(function (html) {
                content.innerHTML = html;
                history.replaceState(null, '', url + '#spread-encyclopedia');
                if (status) status.textContent = 'Showing ' + pill.textContent.trim().toLowerCase();
                var active = content.querySelector('[data-shelf-pill="' + value + '"]');
                if (active) active.focus();
                watchTrack();
            })
            .catch(function () {
                if (window.showToast) window.showToast('Could not load plants', 'Check your connection and try again.', 'error');
            })
            .finally(function () { content.removeAttribute('aria-busy'); });
    });

    window.addEventListener('resize', updateProgress);
    watchTrack();
})();
