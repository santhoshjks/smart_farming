document.addEventListener('DOMContentLoaded', () => {

    // Helper to show results
    function showResult(title, message, icon = '🌱') {
        const overlay = document.getElementById('resultOverlay');
        const titleEl = document.getElementById('resultTitle');
        const msgEl = document.getElementById('resultMessage');
        const iconEl = document.getElementById('resultIcon');

        titleEl.textContent = title;
        msgEl.innerHTML = message; // Allow HTML for formatted response
        iconEl.textContent = icon;

        overlay.classList.add('active');
    }

    // Close modal
    const closeBtn = document.querySelector('.close-btn');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            document.getElementById('resultOverlay').classList.remove('active');
        });
    }

    // Generic Form Handler (only for API forms with data-endpoint)
    const forms = document.querySelectorAll('form[data-endpoint]');
    forms.forEach(form => {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = form.querySelector('button[type="submit"]');
            if (!submitBtn) return;

            const originalBtnText = submitBtn.innerHTML;
            const endpoint = form.dataset.endpoint;
            if (!endpoint) return;

            // Loading state - Create a proper inline spinner
            submitBtn.innerHTML = `
                <span style="
                    display: inline-block;
                    width: 18px;
                    height: 18px;
                    border: 3px solid rgba(255,255,255,0.3);
                    border-top-color: #fff;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin-right: 8px;
                    vertical-align: middle;
                "></span>
                <span style="vertical-align: middle;">Analyzing...</span>
            `;
            submitBtn.disabled = true;

            const formData = new FormData(form);
            let body;
            let headers = {};

            // Handle pure JSON APIs vs File Upload
            if (endpoint.includes('disease')) {
                body = formData; // Send as multipart/form-data
            } else {
                body = JSON.stringify(Object.fromEntries(formData));
                headers['Content-Type'] = 'application/json';
            }

            try {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: headers,
                    body: body
                });

                if (!response.ok) {
                    throw new Error(`Server returned ${response.status}`);
                }

                const data = await response.json();

                if (data.success) {
                    if (endpoint.includes('crop')) {
                        showResult('Recommended Crops', `Based on your inputs, the best crops for you are: <br><div style="font-size: 1.2rem; color: #2ecc71; margin-top: 10px; line-height: 1.6;">${data.prediction}</div>`, '🌾');
                    } else if (endpoint.includes('fertilizer')) {
                        showResult('Recommended Fertilizer', `The best fertilizer for your soil is <br><strong style="font-size: 1.5rem; color: #f1c40f;">${data.prediction}</strong>`, '🧪');
                    } else if (endpoint.includes('disease')) {
                        showResult('Disease Identified', `The plant appears to have <br><strong style="font-size: 1.5rem; color: #e74c3c;">${data.prediction}</strong>`, '🦠');
                    }
                } else {
                    showResult('Error', data.error || 'Something went wrong', '⚠️');
                }
            } catch (error) {
                console.error("Fetch Error:", error);
                showResult('Error', `Connection failed: ${error.message}`, '⚠️');
            } finally {
                submitBtn.innerHTML = originalBtnText;
                submitBtn.disabled = false;
                submitBtn.style.opacity = '1';
                submitBtn.style.cursor = 'pointer';
            }
        });
    });

    // File input preview
    const fileInput = document.querySelector('input[type="file"]');
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            const fileName = e.target.files[0]?.name;
            const label = document.querySelector('.file-upload p');
            if (fileName) {
                label.textContent = `Selected: ${fileName}`;
                label.style.color = '#2ecc71';
            }
        });

    }

    // --- Realtime Weather Logic ---
    const geoBtn = document.getElementById('geoBtn');
    if (geoBtn) {
        geoBtn.addEventListener('click', () => {
            const statusEl = document.getElementById('weatherStatus');
            const seasonSelect = document.getElementById('seasonInput');
            statusEl.style.display = 'block';
            statusEl.textContent = '📍 Locating...';
            statusEl.style.color = '#bdc3c7';

            if (!navigator.geolocation) {
                statusEl.textContent = '❌ Geolocation is not supported by your browser';
                return;
            }

            navigator.geolocation.getCurrentPosition(async (position) => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                statusEl.textContent = `📍 Found (${lat.toFixed(2)}, ${lon.toFixed(2)}). Fetching Weather...`;

                try {
                    // Use Open-Meteo API (Free, No Key needed)
                    const response = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,relative_humidity_2m`);
                    const data = await response.json();

                    const temp = data.current.temperature_2m;
                    const humidity = data.current.relative_humidity_2m;

                    // Set Hidden Inputs
                    document.getElementById('realTemp').value = temp;
                    document.getElementById('realHumidity').value = humidity;

                    // Update UI
                    statusEl.innerHTML = `✅ <strong>${temp}°C,  ${humidity}% Humidity</strong> (Detected)<br>Using real-time data instead of Season selection.`;
                    statusEl.style.color = '#2ecc71';

                    // Optional: Disable season selector to indicate overrides
                    seasonSelect.required = false;
                    seasonSelect.disabled = true;
                    // Provide a dummy value so form doesn't complain if you re-enable validation
                    seasonSelect.value = "summer";

                } catch (error) {
                    console.error(error);
                    statusEl.textContent = '⚠️ Failed to fetch weather data.';
                    statusEl.style.color = '#e74c3c';
                }

            }, () => {
                statusEl.textContent = '❌ Unable to retrieve your location';
                statusEl.style.color = '#e74c3c';
            });
        });
    }

    // --- Logout Confirmation ---
    const logoutLink = document.getElementById('logoutLink');
    const logoutOverlay = document.getElementById('logoutOverlay');
    const cancelLogout = document.getElementById('cancelLogout');

    if (logoutLink && logoutOverlay) {
        logoutLink.addEventListener('click', (e) => {
            e.preventDefault();
            logoutOverlay.classList.add('active');
        });

        cancelLogout.addEventListener('click', () => {
            logoutOverlay.classList.remove('active');
        });

        // Close on clicking outside the card
        logoutOverlay.addEventListener('click', (e) => {
            if (e.target === logoutOverlay) {
                logoutOverlay.classList.remove('active');
            }
        });
    }
});
