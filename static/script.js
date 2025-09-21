// Initializing the Map
var map = L.map('map').setView([7.8592, 125.0515], 13);
var currentMarker = null;
let hourlyChart;
const notifications = []; // Store notifications

// Add tile layer
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19
}).addTo(map);

// Function to update the Windy iframe based on Leaflet map's center and zoom
function updateWindyMap() {
    const center = map.getCenter();
    const zoom = map.getZoom();
    const windyIframe = document.getElementById('windy-iframe');
    windyIframe.src = `https://embed.windy.com/embed.html?type=map&location=${center.lat},${center.lng}&metricRain=default&metricTemp=default&metricWind=default&zoom=${zoom}&overlay=clouds&product=ecmwf&level=surface&lat=${center.lat}&lon=${center.lng}`;
}

updateWindyMap();

// Function to create or update a chart
function createOrUpdateChart(chart, ctx, labels, data, label) {
    if (chart) {
        // Clear existing data
        chart.data.labels = [];
        chart.data.datasets[0].data = [];
        
        chart.data.labels.push(...labels);
        chart.data.datasets[0].data.push(...data);
        chart.update();
    } else {
        chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: label,
                    data: data,
                    borderColor: 'rgba(75, 192, 192, 1)',
                    fill: false,
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: true }
                }
            }
        });
    }
    return chart;
}

// Request Notification permission
if (Notification.permission !== 'granted') {
    Notification.requestPermission();
}

// Function to create or update a chart
function createOrUpdateChart(chart, ctx, labels, data, label) {
    if (chart) {
        // Clear existing data
        chart.data.labels = [];
        chart.data.datasets[0].data = [];
        
        chart.data.labels.push(...labels);
        chart.data.datasets[0].data.push(...data);
        chart.update();
    } else {
        chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: label,
                    data: data,
                    borderColor: 'rgba(75, 192, 192, 1)',
                    fill: false,
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: true }
                }
            }
        });
    }
    return chart;
}

// Function to handle map click
function handleMapClick(e) {
    var lat = e.latlng.lat.toFixed(6);
    var lng = e.latlng.lng.toFixed(6);

    fetchCloudCoverData(lat, lng);
}

// Function to calculate rain probability based on cloud coverage
function calculateRainProbability(totalCloudCover) {
    if (totalCloudCover > 75) return "High chance of rain 🌧️";
    if (totalCloudCover > 50) return "Moderate chance of rain 🌦️";
    if (totalCloudCover > 25) return "Low chance of rain ☁️";
    return "No significant chance of rain 🌤️";
}

// Fetch cloud cover data from server
// Function to calculate rain probability based on cloud coverage
function calculateRainProbability(totalCloudCover) {
    if (totalCloudCover > 75) return "High chance of rain 🌧️";
    if (totalCloudCover > 50) return "Moderate chance of rain 🌦️";
    if (totalCloudCover > 25) return "Low chance of rain ☁️";
    return "No significant chance of rain 🌤️";
}

// Fetch cloud cover data from server
function fetchCloudCoverData(lat, lng) {
    fetch('/get-stored-data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ latitude: lat, longitude: lng })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Fetched Data:', data);  // Add this line for debugging

        if (data.success) {
            updateCloudCoverData(data.current);
            document.getElementById('latitude').innerText = lat;
            document.getElementById('longitude').innerText = lng;

            if (currentMarker) map.removeLayer(currentMarker);
            currentMarker = L.marker([lat, lng]).addTo(map)
                .bindPopup(`Latitude: ${lat}<br>Longitude: ${lng}`)
                .openPopup();

            // Plot hourly cloud cover data
            const hourlyCtx = document.getElementById('hourlyCloudCoverChart').getContext('2d');
            hourlyChart = createOrUpdateChart(
                hourlyChart,
                hourlyCtx,
                data.hourly.time,
                data.hourly.cloud_cover_total, // Correcting to match your data structure
                'Hourly Cloud Cover'
            );

            // Call analyzeSafety with the fetched data
            analyzeSafety(data.current.cloud_cover_total, data.current.visibility);

            // Prepare cloud cover data for the next 2 hours
            const next2HoursCloudCover = data.hourly.cloud_cover_total.slice(0, 2);
            const next2HoursAverageCloudCover = next2HoursCloudCover.reduce((a, b) => a + b, 0) / next2HoursCloudCover.length;
            const next2HoursCloudCoverStr = next2HoursCloudCover.join('% and ') + '%';

            // Calculate rain probability for the next 2 hours
            const next2HoursRainProbability = calculateRainProbability(next2HoursAverageCloudCover);

            // Show notification if needed
            const cloudCoverTotal = data.current.cloud_cover_total;
            const timestamp = data.current.time;  // Use the timestamp from the response
            if (parseInt(cloudCoverTotal) > 80) {
                showBrowserNotification('Warning: High cloud cover detected!');
                addNotification(`High cloud cover detected: ${cloudCoverTotal} at ${timestamp}. Possible cloud cover for the next 2 hours: ${next2HoursCloudCoverStr}. ${next2HoursRainProbability}`);
            } else {
                addNotification(`Normal cloud cover: ${cloudCoverTotal} at ${timestamp}. Possible cloud cover for the next 2 hours: ${next2HoursCloudCoverStr}. ${next2HoursRainProbability}`);
            }
        } else {
            alert(data.message || 'No data found for this location.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while fetching data. Please try again.');
    });
}

// Function to add notifications
function addNotification(message) {
    const notificationList = document.getElementById('notificationList');
    const listItem = document.createElement('li');
    listItem.innerHTML = message;  // Allow HTML tags in the message
    notificationList.appendChild(listItem);
}

// Update cloud cover data in the table
function updateCloudCoverData(data) {
    document.getElementById('cloudCoverTotal').innerText = data.cloud_cover_total || 'N/A';
    document.getElementById('cloudCoverLow').innerText = data.cloud_cover_low || 'N/A';
    document.getElementById('cloudCoverMid').innerText = data.cloud_cover_mid || 'N/A';
    document.getElementById('cloudCoverHigh').innerText = data.cloud_cover_high || 'N/A';
    document.getElementById('visibility').innerText = data.visibility || 'N/A';
}

// Event listener for map clicks
map.on('click', handleMapClick);


////////////////////////
/////  ANALYSIS  //////
//////////////////////

// Function to analyze safety
function analyzeSafety(cloud_cover_total, visibility) {
    // Show placeholder message
    const placeholder = document.getElementById('placeholder');
    if (placeholder) {
        placeholder.style.display = 'block';
        console.log('Placeholder displayed');
    } else {
        console.error('Placeholder element not found');
    }

    // Create the analysis prompt
    const prompt = `
        Analyze the following conditions:
        Total Cloud Cover: ${cloud_cover_total} %,
        Visibility: ${visibility} meters
    `;
    console.log('Prompt created:', prompt);

    // Encode the prompt to ensure it is correctly formatted for a URL
    const encodedPrompt = encodeURIComponent(prompt.trim());
    console.log('Encoded prompt:', encodedPrompt);

    // Set the iframe's source to the analysis URL
    const iframeSrc = `https://barmmdrr.com/connect_ai/message?prompt=${encodedPrompt}`;
    const iframe = document.getElementById('nlpIframe');
    if (iframe) {
        iframe.src = iframeSrc;
        console.log('Iframe src set to:', iframeSrc);

        // Hide the placeholder when the iframe content is loaded
        iframe.onload = function () {
            if (placeholder) {
                placeholder.style.display = 'none';
                console.log('Iframe loaded, placeholder hidden');
            }
        };

        // Handle iframe load errors
        iframe.onerror = function () {
            if (placeholder) {
                placeholder.textContent = 'Failed to load data. Please try again later.';
                placeholder.style.color = 'red';
                console.error('Iframe failed to load');
            }
        };
    } else {
        console.error('Iframe element not found');
    }
}

////////////////////////
///  NOTIFICATION  ////
//////////////////////

// Function to show browser notification
function showBrowserNotification(message) {
    if (Notification.permission === 'granted') {
        new Notification('Weather Alert', {
            body: message,
            icon: '../static/images/cloud-notif.png',
        });
    }
}

// Function to add notification to the dropdown
function addNotification(message) {
    notifications.push(message);

    const badge = document.getElementById('notification-badge');
    badge.textContent = notifications.length;
    badge.style.display = 'block'; // Show the badge
}

// Function to display the dropdown
function toggleDropdown() {
    const dropdown = document.getElementById('notification-menu');
    const notificationList = document.getElementById('notification-list');

    // Clear the dropdown list
    notificationList.innerHTML = '';

    if (notifications.length === 0) {
        const noNotification = document.createElement('li');
        noNotification.textContent = 'No notifications';
        noNotification.classList.add('no-notifications');
        notificationList.appendChild(noNotification);
    } else {
        notifications.forEach(notification => {
            const listItem = document.createElement('li');
            listItem.textContent = notification;
            notificationList.appendChild(listItem);
        });
    }

    // Toggle visibility
    if (dropdown.style.display === 'block') {
        dropdown.style.display = 'none';
    } else {
        dropdown.style.display = 'block';
    }
}

// Close dropdown when clicking outside
document.addEventListener('click', (event) => {
    const dropdown = document.getElementById('notification-menu');
    const container = document.getElementById('notification-container');

    if (!container.contains(event.target)) {
        dropdown.style.display = 'none';
    }
});

// Attach dropdown toggle to notification container click
document.getElementById('notification-container').addEventListener('click', (e) => {
    e.stopPropagation(); // Prevent triggering the document click listener
    toggleDropdown();
});


// Fetch user's first name from the backend
fetch('/get-user-fname')
.then(response => response.json())
.then(data => {
    console.log ('Response from /get-user-fname:', data);  // Debugging line
    if (data.success && data.f_name) {
        document.getElementById('user-name').textContent = data.f_name;
    } else {
        document.getElementById('user-name').textContent = 'Guest';
    }
})
.catch(error => {
    console.error('Error fetching user name:', error);
});

// Function to open the modal and fetch user data
document.getElementById('edit-profile-button').onclick = function() {
    fetch('/edit-profile', {
        method: 'GET',
        credentials: 'include'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const user = data.user;
            document.getElementById('first_name').value = user.f_name || '';
            document.getElementById('last_name').value = user.l_name || '';
            document.getElementById('username').value = user.username || '';
            document.getElementById('email').value = user.email || '';
            // Show the modal
            document.getElementById('edit-profile-modal').style.display = 'block';
        }
    });
};

// Close modal functionality
document.getElementById('close-modal-button').addEventListener('click', function() {
    document.getElementById('edit-profile-modal').style.display = 'none';  // Hide the modal
});

// Handle form submission
document.getElementById('edit-profile-form').onsubmit = function(event) {
    event.preventDefault();
    const formData = new FormData(this);
    
    fetch('/edit-profile', {
        method: 'POST',
        body: formData,
        credentials: 'include'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show a success notification
            const successNotification = document.createElement('div');
            successNotification.className = 'success-notification';
            successNotification.textContent = 'Profile updated successfully!';
            document.body.appendChild(successNotification);

            // Auto-remove the notification after 3 seconds with fade-out effect
            setTimeout(() => {
                successNotification.classList.add('fade-out');
                setTimeout(() => {
                    successNotification.remove();
                }, 500); // Wait for fade-out transition to complete
            }, 2000);

            document.getElementById('edit-profile-modal').style.display = 'none'; // Close the modal
        } else {
            alert(data.message || 'Failed to update profile.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An unexpected error occurred. Please try again later.');
    });
};



// Sidebar Toggle
const sidebar = document.querySelector('.sidebar');
const toggleButton = document.getElementById('sidebar-toggle-btn');

toggleButton.addEventListener('click', function() {
    sidebar.classList.toggle('open');
});

// Handling Logout and User Page Navigation
document.getElementById('logout-btn').addEventListener('click', function() {
    sessionStorage.clear();
    window.location.href = '/';
});

document.getElementById('view-users-btn').addEventListener('click', function() {
    window.location.href = '/all-users';
});

// Dropdown menu toggle
const dropdownButton = document.querySelector('.dropdown-button');
const dropdownMenu = document.querySelector('.dropdown-menu');

dropdownButton.addEventListener('click', function(event) {
    event.stopPropagation(); // Prevent closing when clicking inside the dropdown button
    dropdownMenu.style.display = dropdownMenu.style.display === 'block' ? 'none' : 'block';
});

// Close dropdown menu if clicked outside of it
document.addEventListener('click', function(event) {
    if (!dropdownButton.contains(event.target) && !dropdownMenu.contains(event.target)) {
        dropdownMenu.style.display = 'none';
    }
});
