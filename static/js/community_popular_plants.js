(() => {
    const wrapper = document.getElementById('popular-plants-wrapper');
    if (!wrapper) return;

    async function refreshPopularPlants() {
        try {
            const response = await fetch(wrapper.dataset.endpoint);
            if (!response.ok) {
                throw new Error('status ' + response.status);
            }
            wrapper.innerHTML = await response.text();
        } catch (error) {
            console.error('Could not refresh popular plants:', error);
        }
    }

    window.refreshPopularPlants = refreshPopularPlants;
})();