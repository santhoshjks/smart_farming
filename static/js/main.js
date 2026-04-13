document.addEventListener('DOMContentLoaded', () => {

    // Language state (declared early so all handlers can access it)
    let currentLang = localStorage.getItem('smartfarming_lang') || 'en';

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
            const loadingText = currentLang === 'ta' ? 'பகுப்பாய்வு செய்கிறது...' : 'Analyzing...';
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
                <span style="vertical-align: middle;">${loadingText}</span>
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
                    const isTamil = currentLang === 'ta';
                    if (endpoint.includes('crop')) {
                        let weatherInfo = '';
                        if (data.weather_used) {
                            const w = data.weather_used;
                            const sourceLabel = w.source === 'realtime'
                                ? (isTamil ? '📍 நிகழ்நேர வானிலை தரவு' : '📍 Real-time weather data')
                                : (isTamil ? '📅 பருவ அடிப்படையிலான மதிப்பீடு' : '📅 Season-based estimate');
                            const tempLabel = isTamil ? 'வெப்பநிலை' : '';
                            const humLabel = isTamil ? 'ஈரப்பதம்' : '';
                            weatherInfo = `<div style="font-size: 0.8rem; color: #95a5a6; margin-top: 12px; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px; line-height: 1.8;">
                                ${sourceLabel}${data.location ? ` — ${data.location}` : ''}<br>
                                🌡️ ${w.temperature}°C &nbsp; 💧 ${w.humidity}%
                            </div>`;
                        }
                        const cropTitle = isTamil ? 'பரிந்துரைக்கப்பட்ட பயிர்கள்' : 'Recommended Crops';
                        const cropMsg = isTamil
                            ? `உங்கள் உள்ளீடுகளின் அடிப்படையில், உங்களுக்கு சிறந்த பயிர்கள்: <br><div style="font-size: 1.2rem; color: #2ecc71; margin-top: 10px; line-height: 1.6;">${data.prediction}</div>${weatherInfo}`
                            : `Based on your inputs, the best crops for you are: <br><div style="font-size: 1.2rem; color: #2ecc71; margin-top: 10px; line-height: 1.6;">${data.prediction}</div>${weatherInfo}`;
                        showResult(cropTitle, cropMsg, '🌾');
                    } else if (endpoint.includes('fertilizer')) {
                        const fertTitle = isTamil ? 'பரிந்துரைக்கப்பட்ட உரம்' : 'Recommended Fertilizer';
                        const fertMsg = isTamil
                            ? `உங்கள் மண்ணுக்கு சிறந்த உரம் <br><strong style="font-size: 1.5rem; color: #f1c40f;">${data.prediction}</strong>`
                            : `The best fertilizer for your soil is <br><strong style="font-size: 1.5rem; color: #f1c40f;">${data.prediction}</strong>`;
                        showResult(fertTitle, fertMsg, '🧪');
                    } else if (endpoint.includes('disease')) {
                        const diseaseTitle = isTamil ? 'நோய் கண்டறியப்பட்டது' : 'Disease Identified';
                        const diseaseMsg = isTamil
                            ? `இந்த தாவரத்தில் காணப்படும் நோய் <br><strong style="font-size: 1.5rem; color: #e74c3c;">${data.prediction}</strong>`
                            : `The plant appears to have <br><strong style="font-size: 1.5rem; color: #e74c3c;">${data.prediction}</strong>`;
                        showResult(diseaseTitle, diseaseMsg, '🦠');
                    }
                } else {
                    const errTitle = currentLang === 'ta' ? 'பிழை' : 'Error';
                    const errFallback = currentLang === 'ta' ? 'ஏதோ தவறு ஏற்பட்டது' : 'Something went wrong';
                    showResult(errTitle, data.error || errFallback, '⚠️');
                }
            } catch (error) {
                console.error("Fetch Error:", error);
                const errTitle = currentLang === 'ta' ? 'பிழை' : 'Error';
                const connFail = currentLang === 'ta' ? 'இணைப்பு தோல்வி' : 'Connection failed';
                showResult(errTitle, `${connFail}: ${error.message}`, '⚠️');
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
                const selectedText = currentLang === 'ta' ? 'தேர்ந்தெடுக்கப்பட்டது' : 'Selected';
                label.textContent = `${selectedText}: ${fileName}`;
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
            const weatherCard = document.getElementById('weatherCard');
            const isTa = currentLang === 'ta';

            statusEl.style.display = 'block';
            statusEl.textContent = isTa ? '📍 இருப்பிடத்தைக் கண்டறிகிறது...' : '📍 Locating...';
            statusEl.style.color = '#bdc3c7';

            // Disable button during fetch
            geoBtn.disabled = true;
            geoBtn.innerHTML = '<span class="spinner-small" style="display:inline-block; width:12px; height:12px; border:2px solid rgba(255,255,255,0.3); border-top-color:#fff; border-radius:50%; animation:spin 1s linear infinite; margin-right:8px;"></span> ' + (isTa ? 'கண்டறிகிறது...' : 'Detecting...');

            if (!navigator.geolocation) {
                statusEl.textContent = isTa ? '❌ உங்கள் உலாவி புவி இருப்பிடத்தை ஆதரிக்கவில்லை' : '❌ Geolocation is not supported by your browser';
                geoBtn.disabled = false;
                geoBtn.textContent = isTa ? '📍 உண்மையான இருப்பிடத்தைப் பயன்படுத்து' : '📍 Use Real Location';
                return;
            }

            navigator.geolocation.getCurrentPosition(async (position) => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                statusEl.textContent = isTa
                    ? `📍 கண்டறியப்பட்டது (${lat.toFixed(2)}, ${lon.toFixed(2)}). வானிலை பெறுகிறது...`
                    : `📍 Found (${lat.toFixed(2)}, ${lon.toFixed(2)}). Fetching weather...`;

                try {
                    // Fetch current weather + daily rainfall from Open-Meteo
                    const weatherUrl = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,relative_humidity_2m&daily=precipitation_sum&timezone=auto&forecast_days=1`;
                    const weatherRes = await fetch(weatherUrl);
                    const weatherData = await weatherRes.json();

                    const temp = weatherData.current.temperature_2m;
                    const humidity = weatherData.current.relative_humidity_2m;

                    // Reverse geocode for location name
                    let locationName = `${lat.toFixed(2)}°, ${lon.toFixed(2)}°`;
                    try {
                        const geoUrl = `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&zoom=10`;
                        const geoRes = await fetch(geoUrl, {
                            headers: { 'Accept-Language': isTa ? 'ta' : 'en' }
                        });
                        const geoData = await geoRes.json();
                        const addr = geoData.address || {};
                        locationName = [addr.city || addr.town || addr.village || addr.county, addr.state, addr.country]
                            .filter(Boolean).join(', ');
                    } catch (e) {
                        console.warn('Reverse geocode failed, using coords', e);
                    }

                    // Set hidden form inputs
                    document.getElementById('realTemp').value = temp;
                    document.getElementById('realHumidity').value = humidity;
                    document.getElementById('locationNameInput').value = locationName;

                    // Update the weather card
                    if (weatherCard) {
                        document.getElementById('locationName').textContent = locationName;
                        document.getElementById('cardTemp').textContent = `${temp}°C`;
                        document.getElementById('cardHumidity').textContent = `${humidity}%`;
                        weatherCard.style.display = 'block';
                    }

                    // Update status text with a polished look
                    statusEl.innerHTML = `<span style="opacity: 0.8;">📍</span> ${locationName} <span style="margin: 0 8px; opacity: 0.3;">|</span> <span style="color:#fff; font-weight:600;">${temp}°C</span>`;
                    statusEl.style.color = '#3498db';
                    statusEl.style.fontSize = '0.85rem';
                    statusEl.style.fontWeight = '500';
                    statusEl.style.letterSpacing = '0.3px';

                    // Disable season selector (real data overrides it)
                    seasonSelect.required = false;
                    seasonSelect.disabled = true;
                    seasonSelect.value = 'summer'; // dummy value

                    // Update button to show success
                    geoBtn.innerHTML = isTa ? '✅ இருப்பிடம் செயலில்' : '✅ Location Active';
                    geoBtn.style.borderColor = '#2ecc71';
                    geoBtn.style.color = '#fff';
                    geoBtn.style.background = 'rgba(46, 204, 113, 0.1)';

                } catch (error) {
                    console.error(error);
                    statusEl.textContent = isTa ? '⚠️ வானிலை தரவைப் பெற இயலவில்லை. பருவத்தைத் தேர்ந்தெடுக்கவும்.' : '⚠️ Failed to fetch weather data. Using season selection.';
                    statusEl.style.color = '#e74c3c';
                    geoBtn.disabled = false;
                    geoBtn.textContent = isTa ? '📍 உண்மையான இருப்பிடத்தைப் பயன்படுத்து' : '📍 Use Real Location';
                }

            }, (err) => {
                console.error('Geolocation error:', err);
                statusEl.textContent = isTa ? '❌ உங்கள் இருப்பிடத்தைப் பெற இயலவில்லை. பருவத்தை கைமுறையாகத் தேர்ந்தெடுக்கவும்.' : '❌ Unable to retrieve your location. Please select a season manually.';
                statusEl.style.color = '#e74c3c';
                geoBtn.disabled = false;
                geoBtn.textContent = isTa ? '📍 உண்மையான இருப்பிடத்தைப் பயன்படுத்து' : '📍 Use Real Location';
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

    // Mobile logout link also triggers the confirmation dialog
    const mobileLogoutLink = document.getElementById('mobileLogoutLink');
    if (mobileLogoutLink && logoutOverlay) {
        mobileLogoutLink.addEventListener('click', (e) => {
            e.preventDefault();
            // Close hamburger menu first
            const hamburger = document.getElementById('hamburgerBtn');
            const navLinksEl = document.getElementById('navLinks');
            if (hamburger) hamburger.classList.remove('active');
            if (navLinksEl) navLinksEl.classList.remove('open');
            // Show confirmation
            logoutOverlay.classList.add('active');
        });
    }
    // --- Hamburger Menu Toggle ---
    const hamburgerBtn = document.getElementById('hamburgerBtn');
    const navLinks = document.getElementById('navLinks');

    if (hamburgerBtn && navLinks) {
        hamburgerBtn.addEventListener('click', () => {
            hamburgerBtn.classList.toggle('active');
            navLinks.classList.toggle('open');
        });

        // Close menu when a link is clicked
        navLinks.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                hamburgerBtn.classList.remove('active');
                navLinks.classList.remove('open');
            });
        });
    }

    // =============================================
    //   TAMIL LANGUAGE TRANSLATION SYSTEM
    // =============================================
    const tamilTranslations = {
        // Navigation
        'Home': 'முகப்பு',
        'Crop Recommendation': 'பயிர் பரிந்துரை',
        'Fertilizer': 'உரம்',
        'Disease Check': 'நோய் கண்டறிதல்',
        'Simulator': 'உருவகப்படுத்தி',
        'Login': 'உள்நுழை',
        'Register': 'பதிவு செய்',
        'Logout': 'வெளியேறு',

        // Hero Section
        'The Future of Agriculture is Here': 'விவசாயத்தின் எதிர்காலம் இங்கே',
        'Leverage the power of AI to optimize your harvest. Get personalized crop recommendations, precise fertilizer suggestions, and instant plant disease diagnosis.': 'AI-யின் சக்தியைப் பயன்படுத்தி உங்கள் அறுவடையை மேம்படுத்துங்கள். தனிப்பயனாக்கப்பட்ட பயிர் பரிந்துரைகள், துல்லியமான உர ஆலோசனைகள் மற்றும் உடனடி தாவர நோய் கண்டறிதல் பெறுங்கள்.',
        'Get Started': 'தொடங்குங்கள்',
        'Learn More': 'மேலும் அறிய',

        // Feature Cards
        'Crop Recommendation': 'பயிர் பரிந்துரை',
        'Select your soil type and let real-time location weather data power intelligent crop recommendations.': 'உங்கள் மண் வகையைத் தேர்ந்தெடுத்து, நிகழ்நேர வானிலை தரவுகளின் மூலம் புத்திசாலித்தனமான பயிர் பரிந்துரைகளைப் பெறுங்கள்.',
        'Fertilizer Advisor': 'உர ஆலோசகர்',
        'Get tailored fertilizer recommendations based on soil nutrient depletion to restore health.': 'மண்ணின் ஊட்டச்சத்து குறைபாட்டின் அடிப்படையில் தனிப்பயனாக்கப்பட்ட உர பரிந்துரைகளைப் பெறுங்கள்.',
        'Disease Detection': 'நோய் கண்டறிதல்',
        'Upload a photo of your plant leaf and let our AI diagnose diseases and suggest cures instantly.': 'உங்கள் தாவர இலையின் புகைப்படத்தைப் பதிவேற்றி, எங்கள் AI உடனடியாக நோய்களைக் கண்டறிந்து தீர்வுகளை பரிந்துரைக்கட்டும்.',
        'Crop Simulator': 'பயிர் உருவகப்படுத்தி',
        'Simulate crop growth over time with adjustable weather, soil, and irrigation parameters to plan your harvest.': 'வானிலை, மண் மற்றும் நீர்ப்பாசன அளவுருக்களை மாற்றி, காலப்போக்கில் பயிர் வளர்ச்சியை உருவகப்படுத்துங்கள்.',

        // Crop Recommendation Page
        '🌾 Crop Recommendation': '🌾 பயிர் பரிந்துரை',
        'Enter soil and weather conditions to find the most suitable crop.': 'மிகவும் பொருத்தமான பயிரைக் கண்டறிய மண் மற்றும் வானிலை நிலைகளை உள்ளிடுங்கள்.',
        'What does your soil look like? (Soil Type)': 'உங்கள் மண் எப்படி இருக்கிறது? (மண் வகை)',
        'Select Soil Appearance': 'மண் தோற்றத்தைத் தேர்ந்தெடுக்கவும்',
        'Clay (Sticky, holds water, usually dark/heavy)': 'களிமண் (ஒட்டும், தண்ணீர் தேக்கும், கருமையானது)',
        'Sandy (Gritty, drains fast, light color)': 'மணல் (சரளை, வேகமாக வடியும், வெளிர் நிறம்)',
        'Loamy (Crumbly, dark, best for gardens)': 'களிமண் (நொறுங்கும், கருமை, தோட்டத்திற்கு சிறந்தது)',
        'Black (Dark black, cracks when dry)': 'கருப்பு (அடர் கருப்பு, உலர்ந்தால் வெடிக்கும்)',
        'Red (Reddish color, often dusty)': 'சிவப்பு (சிவப்பு நிறம், பெரும்பாலும் புழுதி)',
        'Current Season / Weather': 'தற்போதைய பருவம் / வானிலை',
        'Select Current Season': 'தற்போதைய பருவத்தைத் தேர்ந்தெடுக்கவும்',
        'Summer (Hot & Dry)': 'கோடை (வெப்பமும் வறட்சியும்)',
        'Winter (Cold & Dry)': 'குளிர்காலம் (குளிரும் வறட்சியும்)',
        'Monsoon / Rainy (Wet & Humid)': 'பருவமழை (ஈரமும் ஈரப்பதமும்)',
        'Autumn / Pleasant': 'இலையுதிர் / இதமான',
        '📍 Use Real Location': '📍 உண்மையான இருப்பிடத்தைப் பயன்படுத்து',
        'Water Availability': 'நீர் கிடைக்கும் தன்மை',
        'Low (Depend on rain only)': 'குறைவு (மழையை மட்டும் நம்பி)',
        'Medium (Can water occasionally)': 'நடுத்தர (எப்போதாவது நீர் பாய்ச்சலாம்)',
        'High (Good irrigation / abundant water)': 'அதிகம் (நல்ல நீர்ப்பாசனம் / நிறைய தண்ணீர்)',
        'Recommend Best Crop': 'சிறந்த பயிரைப் பரிந்துரைக்கவும்',

        // Fertilizer Page
        '🧪 Fertilizer Advisor': '🧪 உர ஆலோசகர்',
        'Optimize your soil health with the right nutrients.': 'சரியான ஊட்டச்சத்துகளுடன் உங்கள் மண் ஆரோக்கியத்தை மேம்படுத்துங்கள்.',
        'What crop are you growing?': 'நீங்கள் என்ன பயிர் விளைவிக்கிறீர்கள்?',
        'Select Crop': 'பயிரைத் தேர்ந்தெடுக்கவும்',
        'Wheat': 'கோதுமை',
        'Rice / Paddy': 'அரிசி / நெல்',
        'Maize / Corn': 'மக்காச்சோளம்',
        'Cotton': 'பருத்தி',
        'Sugarcane': 'கரும்பு',
        'Pulses / Beans': 'பயறு வகைகள்',
        'Groundnuts / Peanuts': 'நிலக்கடலை',
        'Millets (Bajra/Jowar)': 'தினை வகைகள் (கம்பு/சோளம்)',
        'Soil Type': 'மண் வகை',
        'Sandy (Gritty)': 'மணல் (சரளை)',
        'Loamy (Crumbly)': 'களிமண் (நொறுங்கும்)',
        'Black (Clay-like)': 'கருப்பு (களிமண் போன்ற)',
        'Red (Dusty)': 'சிவப்பு (புழுதி)',
        'Clayey (Sticky)': 'களிமண் (ஒட்டும்)',
        'Land Size': 'நிலத்தின் அளவு',
        'Acres': 'ஏக்கர்',
        'Hectares': 'ஹெக்டேர்',
        'Sq. Meters': 'சதுர மீட்டர்',
        'Plant Condition / Symptoms': 'தாவர நிலை / அறிகுறிகள்',
        'Healthy / Routine Care': 'ஆரோக்கியமான / வழக்கமான பராமரிப்பு',
        'Leaves turning yellow (Chlorosis)': 'இலைகள் மஞ்சள் நிறமாதல் (குளோரோசிஸ்)',
        'Stunted Growth (Small plants)': 'வளர்ச்சி குன்றிய (சிறிய செடிகள்)',
        'Weak Roots / Falling over': 'பலவீனமான வேர்கள் / சாய்தல்',
        'Purplish tint on leaves': 'இலைகளில் ஊதா நிறம்',
        'Burnt/dried leaf edges': 'எரிந்த/உலர்ந்த இலை விளிம்புகள்',
        'Get Fertilizer Advice': 'உர ஆலோசனை பெறுங்கள்',

        // Disease Detection Page
        '🦠 Disease Detection': '🦠 நோய் கண்டறிதல்',
        'Upload a clear photo of the plant leaf for AI-powered diagnosis.': 'AI மூலம் நோய் கண்டறிய தாவர இலையின் தெளிவான புகைப்படத்தைப் பதிவேற்றுங்கள்.',
        'Click or Drag & Drop': 'கிளிக் செய்யவும் அல்லது இழுத்து விடவும்',
        'an image here to upload': 'படத்தை இங்கே பதிவேற்றவும்',
        '🔬 Analyze Image': '🔬 படத்தை ஆய்வு செய்',
        'Tips for best results:': 'சிறந்த முடிவுகளுக்கான குறிப்புகள்:',
        '• Use natural lighting for clearer colors': '• தெளிவான நிறங்களுக்கு இயற்கை வெளிச்சத்தைப் பயன்படுத்துங்கள்',
        '• Focus on a single leaf with visible symptoms': '• தெரியும் அறிகுறிகளுடன் ஒரு இலையில் கவனம் செலுத்துங்கள்',
        '• Avoid blurry or dark images': '• மங்கலான அல்லது இருண்ட படங்களைத் தவிர்க்கவும்',

        // Simulation Page
        '🌱 Crop Growth Simulator': '🌱 பயிர் வளர்ச்சி உருவகப்படுத்தி',
        'Adjust parameters and watch your crop grow from seed to harvest. Plan your season with confidence.': 'அளவுருக்களை மாற்றி, விதையிலிருந்து அறுவடை வரை உங்கள் பயிர் வளர்வதைப் பாருங்கள்.',
        'Select Crop': 'பயிரைத் தேர்ந்தெடுக்கவும்',
        'Rainfall': 'மழையளவு',
        'Temperature': 'வெப்பநிலை',
        'Irrigation Level': 'நீர்ப்பாசன அளவு',
        '▶ Run Simulation': '▶ உருவகப்படுத்தலை இயக்கு',
        'Seed': 'விதை',
        'Sprout': 'முளை',
        'Vegetative': 'வளர்ச்சி',
        'Flowering': 'பூத்தல்',
        'Harvest': 'அறுவடை',
        'Days': 'நாட்கள்',
        'Est. Yield': 'மதிப்பிடப்பட்ட விளைச்சல்',
        'Water Need': 'நீர் தேவை',
        'Risk Level': 'ஆபத்து நிலை',
        // Simulation crop options
        '🌾 Rice (120 days)': '🌾 அரிசி (120 நாட்கள்)',
        '🌿 Wheat (150 days)': '🌿 கோதுமை (150 நாட்கள்)',
        '🌽 Maize (90 days)': '🌽 மக்காச்சோளம் (90 நாட்கள்)',
        '🧶 Cotton (180 days)': '🧶 பருத்தி (180 நாட்கள்)',
        '🎋 Sugarcane (360 days)': '🎋 கரும்பு (360 நாட்கள்)',
        // Simulation soil options
        'Loamy (Best)': 'களிமண் (சிறந்தது)',
        'Clay': 'களிமண்',
        'Sandy': 'மணல்',
        'Black': 'கருப்பு',
        'Red': 'சிவப்பு',
        // Day counter
        'Day': 'நாள்',

        // Login Page
        'Welcome Back': 'மீண்டும் வருக',
        'Sign in to access your SmartFarming dashboard': 'SmartFarming டாஷ்போர்டை அணுக உள்நுழையவும்',
        'Email Address': 'மின்னஞ்சல் முகவரி',
        'Password': 'கடவுச்சொல்',
        'Remember me': 'என்னை நினைவில் கொள்',
        'Sign In': 'உள்நுழை',
        "Don't have an account?": 'கணக்கு இல்லையா?',
        'Create one': 'ஒன்றை உருவாக்கு',
        'or': 'அல்லது',
        '← Back to Home': '← முகப்புக்குத் திரும்பு',
        'Smart Farming AI': 'ஸ்மார்ட் விவசாய AI',
        'Get personalized crop recommendations, fertilizer suggestions, disease detection and crop simulation powered by AI.': 'AI மூலம் தனிப்பயனாக்கப்பட்ட பயிர் பரிந்துரைகள், உர ஆலோசனைகள், நோய் கண்டறிதல் மற்றும் பயிர் உருவகப்படுத்தல் பெறுங்கள்.',
        'Crop Recommendations': 'பயிர் பரிந்துரைகள்',
        'Fertilizer Analysis': 'உர பகுப்பாய்வு',

        // Register Page
        'Create Account': 'கணக்கை உருவாக்கு',
        'Join SmartFarming to unlock all features': 'அனைத்து அம்சங்களையும் திறக்க SmartFarming-ல் இணையுங்கள்',
        'Username': 'பயனர்பெயர்',
        'Confirm Password': 'கடவுச்சொல்லை உறுதிப்படுத்து',
        'Already have an account?': 'ஏற்கனவே கணக்கு உள்ளதா?',
        'Sign in': 'உள்நுழை',
        'Create Your Account': 'உங்கள் கணக்கை உருவாக்கு',

        // Contact Section
        '📬 Get In Touch': '📬 தொடர்பு கொள்ளுங்கள்',
        'Have questions or need support? We\'d love to hear from you.': 'கேள்விகள் அல்லது ஆதரவு தேவையா? உங்களிடமிருந்து கேட்க விரும்புகிறோம்.',
        'GitHub': 'GitHub',
        'Email': 'மின்னஞ்சல்',
        'Phone': 'தொலைபேசி',
        'Location': 'இடம்',
        'Chennai, Tamil Nadu, India': 'சென்னை, தமிழ்நாடு, இந்தியா',
        'Working Hours': 'வேலை நேரம்',
        'Mon – Sat, 9:00 AM – 6:00 PM': 'திங்கள் – சனி, காலை 9:00 – மாலை 6:00',

        // Result Modal
        'Result': 'முடிவு',
        'Analysis complete.': 'பகுப்பாய்வு முடிந்தது.',
        'Leaving So Soon?': 'இவ்வளவு சீக்கிரம் செல்கிறீர்களா?',
        'Are you sure you want to log out of SmartFarming AI?': 'SmartFarming AI-யிலிருந்து வெளியேற விரும்புகிறீர்களா?',
        '✕ Stay': '✕ இருக்கவும்',
        '🚪 Logout': '🚪 வெளியேறு',
        'Report Issue': 'சிக்கலைப் புகாரளி',

        // Weather Card
        'Detecting Location...': 'இருப்பிடத்தைக் கண்டறிகிறது...',
        'LIVE': 'நேரடி',
        'Humidity': 'ஈரப்பதம்',
        'Accuracy optimized for current local conditions': 'தற்போதைய உள்ளூர் நிலைகளுக்கு துல்லியம் மேம்படுத்தப்பட்டது',

        // Simulation Results
        'Low': 'குறைவு',
        'Medium': 'நடுத்தர',
        'High': 'அதிகம்',
        'Moderate': 'மிதமான',
        'Critical': 'ஆபத்தான',

        // Crop Simulation
        'Crop Simulation': 'பயிர் உருவகப்படுத்தல்',

        // Misc
        '🚪 Logout': '🚪 வெளியேறு',
        '🔑 Login': '🔑 உள்நுழை',
        '📝 Register': '📝 பதிவு செய்',
    };

    // Reverse map for switching back
    const englishTranslations = {};
    for (const [en, ta] of Object.entries(tamilTranslations)) {
        englishTranslations[ta] = en;
    }

    // currentLang is declared at the top of DOMContentLoaded scope

    function translatePage(toLang) {
        const dict = toLang === 'ta' ? tamilTranslations : englishTranslations;

        // Walk text nodes of the document body
        const walker = document.createTreeWalker(
            document.body,
            NodeFilter.SHOW_TEXT,
            {
                acceptNode: function (node) {
                    // Skip script/style
                    const parent = node.parentElement;
                    if (!parent) return NodeFilter.FILTER_REJECT;
                    const tag = parent.tagName;
                    if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'CANVAS') return NodeFilter.FILTER_REJECT;
                    // Skip hidden inputs
                    if (tag === 'INPUT' || tag === 'TEXTAREA') return NodeFilter.FILTER_REJECT;
                    return NodeFilter.FILTER_ACCEPT;
                }
            }
        );

        const textNodes = [];
        while (walker.nextNode()) textNodes.push(walker.currentNode);

        textNodes.forEach(node => {
            const original = node.textContent.trim();
            if (original && dict[original]) {
                node.textContent = node.textContent.replace(original, dict[original]);
            }
        });

        // Translate <option> elements
        document.querySelectorAll('option').forEach(opt => {
            const text = opt.textContent.trim();
            if (text && dict[text]) {
                opt.textContent = dict[text];
            }
        });

        // Translate placeholder attributes
        const placeholderMap = {
            'en': {
                'Enter your email': 'உங்கள் மின்னஞ்சலை உள்ளிடுங்கள்',
                'Enter your password': 'உங்கள் கடவுச்சொல்லை உள்ளிடுங்கள்',
                'e.g. 2.5': 'எ.கா. 2.5',
                'Enter your username': 'உங்கள் பயனர்பெயரை உள்ளிடுங்கள்',
                'Confirm your password': 'கடவுச்சொல்லை உறுதிப்படுத்துங்கள்'
            },
            'ta': {
                'உங்கள் மின்னஞ்சலை உள்ளிடுங்கள்': 'Enter your email',
                'உங்கள் கடவுச்சொல்லை உள்ளிடுங்கள்': 'Enter your password',
                'எ.கா. 2.5': 'e.g. 2.5',
                'உங்கள் பயனர்பெயரை உள்ளிடுங்கள்': 'Enter your username',
                'கடவுச்சொல்லை உறுதிப்படுத்துங்கள்': 'Confirm your password'
            }
        };

        const phMap = toLang === 'ta' ? placeholderMap['en'] : placeholderMap['ta'];
        document.querySelectorAll('input[placeholder]').forEach(input => {
            const ph = input.getAttribute('placeholder');
            if (ph && phMap[ph]) {
                input.setAttribute('placeholder', phMap[ph]);
            }
        });

        // Translate page title
        if (toLang === 'ta') {
            document.title = 'ஸ்மார்ட் விவசாயம் AI';
        } else {
            document.title = 'SmartFarming AI';
        }
    }

    // Language toggle button
    const langToggleBtn = document.getElementById('langToggleBtn');
    const langIcon = document.getElementById('langIcon');
    const langLabelEl = document.getElementById('langLabel');

    function setLangUI(lang) {
        if (lang === 'ta') {
            langIcon.textContent = 'த';
            langLabelEl.textContent = 'English';
            langToggleBtn.classList.add('tamil-active');
            langToggleBtn.title = 'Switch to English / ஆங்கிலத்திற்கு மாற்றவும்';
        } else {
            langIcon.textContent = 'EN';
            langLabelEl.textContent = 'தமிழ்';
            langToggleBtn.classList.remove('tamil-active');
            langToggleBtn.title = 'Switch to Tamil / தமிழுக்கு மாற்றவும்';
        }
    }

    if (langToggleBtn) {
        // Apply saved language on page load
        if (currentLang === 'ta') {
            translatePage('ta');
            setLangUI('ta');
        }

        langToggleBtn.addEventListener('click', () => {
            if (currentLang === 'en') {
                translatePage('ta');
                currentLang = 'ta';
            } else {
                translatePage('en');
                currentLang = 'en';
            }
            setLangUI(currentLang);
            localStorage.setItem('smartfarming_lang', currentLang);

            // Micro-animation feedback
            langToggleBtn.style.transform = 'scale(1.2)';
            setTimeout(() => { langToggleBtn.style.transform = ''; }, 200);
        });
    }
});
