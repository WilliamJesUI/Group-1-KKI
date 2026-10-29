(() => {
    const wrapper = document.getElementById('popular-plants-wrapper');
    if (!wrapper) return;

    async function refreshPopularPlants() {
        try {
            // Send the chosen plant along, so it stays highlighted in the new box
            const plant = new URLSearchParams(window.location.search).get('plant') || '';
            const response = await fetch(wrapper.dataset.endpoint + (plant ? '?plant=' + encodeURIComponent(plant) : ''));
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