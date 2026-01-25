/**
 * Sunset Collections Gallery
 *
 * Focused gallery for browsing and playing monthly sunset video compilations.
 */

// DOM Elements
const loadingEl = document.getElementById('loading');
const monthsGridEl = document.getElementById('months-grid');
const videoModalEl = document.getElementById('video-modal');
const modalTitleEl = document.getElementById('modal-title');
const closeModalBtn = document.getElementById('close-modal');
const modalBackdrop = document.querySelector('.modal-backdrop');
const videoEl = document.getElementById('video');
const videoSourceEl = document.getElementById('video-source');
const videoLoadingEl = document.getElementById('video-loading');
const loadingTextEl = document.getElementById('loading-text');
const modalMetaEl = document.getElementById('modal-meta');
const yearFilterEl = document.getElementById('year-filter');

// State
let monthsData = [];
let currentYear = '';

// Month names
const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
];

/**
 * Format duration in seconds to MM:SS or HH:MM:SS
 */
function formatDuration(seconds) {
    if (!seconds) return '--:--';
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
        return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Format file size to human readable
 */
function formatSize(bytes) {
    if (!bytes) return '--';
    const mb = bytes / (1024 * 1024);
    if (mb < 1000) {
        return `${mb.toFixed(1)} MB`;
    }
    return `${(mb / 1024).toFixed(2)} GB`;
}

/**
 * Get collage thumbnail URL for a month (sunset)
 */
function getThumbnailUrl(year, month) {
    const monthStr = month.toString().padStart(2, '0');
    return `https://storage.googleapis.com/fogcat-webcam/${year}/${monthStr}/collages/collage-${year}-${monthStr}-sunset-5x6.jpg`;
}

/**
 * Fetch available months from API
 */
async function fetchMonths() {
    const response = await fetch(`${API_BASE}/api/months`);
    if (!response.ok) {
        throw new Error(`Failed to fetch months: ${response.status}`);
    }
    const data = await response.json();
    return data.months || [];
}

/**
 * Generate or retrieve a sunset compilation
 */
async function generateCompilation(year, month) {
    const params = new URLSearchParams({
        year: year.toString(),
        month: month.toString(),
        time_filter: 'sunset'
    });

    const response = await fetch(`${API_BASE}/api/compilation/generate?${params}`, {
        method: 'POST'
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to generate compilation');
    }

    return response.json();
}

/**
 * Create a month card element
 */
function createMonthCard(monthData) {
    const card = document.createElement('div');
    card.className = 'month-card';

    // Only show months with sunset videos
    if (monthData.sunset_count === 0) {
        return null;
    }

    const monthName = monthNames[monthData.month - 1];
    const thumbnailUrl = getThumbnailUrl(monthData.year, monthData.month);
    const isCompiled = monthData.has_sunset_compilation;

    card.innerHTML = `
        <div class="card-thumbnail">
            <img src="${thumbnailUrl}" alt="${monthName} ${monthData.year} Sunsets"
                 onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
            <div class="thumbnail-placeholder" style="display: none;">
                <span class="sunset-icon"></span>
            </div>
            ${isCompiled ? '<span class="ready-badge">Ready</span>' : ''}
        </div>
        <div class="card-info">
            <h3>${monthName} ${monthData.year}</h3>
            <p class="video-count">${monthData.sunset_count} sunset videos</p>
        </div>
    `;

    card.addEventListener('click', () => {
        playCompilation(monthData.year, monthData.month, monthName);
    });

    return card;
}

/**
 * Render the months grid
 */
function renderMonths() {
    monthsGridEl.innerHTML = '';

    let filtered = monthsData.filter(m => m.sunset_count > 0);

    if (currentYear) {
        filtered = filtered.filter(m => m.year.toString() === currentYear);
    }

    if (filtered.length === 0) {
        monthsGridEl.innerHTML = `
            <div class="empty-state">
                <span class="sunset-icon large"></span>
                <h3>No sunset videos found</h3>
                <p>Try selecting a different year</p>
            </div>
        `;
        return;
    }

    filtered.forEach(monthData => {
        const card = createMonthCard(monthData);
        if (card) {
            monthsGridEl.appendChild(card);
        }
    });
}

/**
 * Populate year filter dropdown
 */
function populateYearFilter() {
    const years = [...new Set(monthsData.filter(m => m.sunset_count > 0).map(m => m.year))].sort((a, b) => b - a);

    yearFilterEl.innerHTML = '<option value="">All Years</option>';
    years.forEach(year => {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        yearFilterEl.appendChild(option);
    });
}

/**
 * Play a sunset compilation
 */
async function playCompilation(year, month, monthName) {
    modalTitleEl.textContent = `${monthName} ${year} Sunsets`;
    videoModalEl.classList.remove('hidden');
    videoLoadingEl.classList.remove('hidden');
    loadingTextEl.textContent = 'Loading sunset compilation...';
    videoEl.style.display = 'none';
    modalMetaEl.innerHTML = '';

    document.body.style.overflow = 'hidden';

    try {
        const result = await generateCompilation(year, month);

        modalMetaEl.innerHTML = `
            <div class="meta-item">
                <span class="meta-label">Videos</span>
                <span class="meta-value">${result.video_count || '--'}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Duration</span>
                <span class="meta-value">${formatDuration(result.duration_seconds)}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Size</span>
                <span class="meta-value">${formatSize(result.size_bytes)}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Status</span>
                <span class="meta-value">${result.cached ? 'Cached' : 'Just Generated'}</span>
            </div>
        `;

        videoSourceEl.src = result.url;
        videoEl.load();
        videoEl.style.display = 'block';
        videoLoadingEl.classList.add('hidden');

        videoEl.play().catch(err => {
            console.log('Auto-play prevented:', err);
        });

    } catch (error) {
        console.error('Error loading compilation:', error);
        loadingTextEl.textContent = `Error: ${error.message}`;
    }
}

/**
 * Close the video modal
 */
function closeModal() {
    videoEl.pause();
    videoModalEl.classList.add('hidden');
    document.body.style.overflow = '';
}

/**
 * Initialize the application
 */
async function init() {
    // Event listeners
    closeModalBtn.addEventListener('click', closeModal);
    modalBackdrop.addEventListener('click', closeModal);

    yearFilterEl.addEventListener('change', (e) => {
        currentYear = e.target.value;
        renderMonths();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !videoModalEl.classList.contains('hidden')) {
            closeModal();
        }
    });

    // Fetch and display months
    try {
        monthsData = await fetchMonths();
        populateYearFilter();
        loadingEl.style.display = 'none';
        renderMonths();
    } catch (error) {
        console.error('Failed to load gallery:', error);
        loadingEl.innerHTML = `
            <div class="error-state">
                <h3>Failed to load sunset collections</h3>
                <p>${error.message}</p>
                <button onclick="location.reload()">Retry</button>
            </div>
        `;
    }
}

document.addEventListener('DOMContentLoaded', init);
