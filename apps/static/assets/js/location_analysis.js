function getColors(count) {
    const baseColors = [
        'rgba(74, 222, 128, 0.6)',
        'rgba(59, 130, 246, 0.6)',
        'rgba(250, 204, 21, 0.6)',
        'rgba(239, 68, 68, 0.6)',
        'rgba(147, 51, 234, 0.6)'
    ];
    const colors = [];
    for (let i = 0; i < count; i++) {
        colors.push(baseColors[i % baseColors.length]);
    }
    return colors;
}

function initializeLocationAnalysis(locationData, predictionChartData, cropChartData, soilChartData, summaryData) {
    // Initialize Map
    if (locationData && locationData.length > 0) {
        const validLocations = locationData.filter(loc => 
            loc.latitude >= -90 && loc.latitude <= 90 && 
            loc.longitude >= -180 && loc.longitude <= 180
        );
        
        if (validLocations.length > 0) {
            const latitudes = validLocations.map(loc => loc.latitude);
            const longitudes = validLocations.map(loc => loc.longitude);
            const avgLat = latitudes.reduce((sum, lat) => sum + lat, 0) / validLocations.length;
            const avgLon = longitudes.reduce((sum, lon) => sum + lon, 0) / validLocations.length;
            const latRange = Math.max(...latitudes) - Math.min(...latitudes);
            const lonRange = Math.max(...longitudes) - Math.min(...longitudes);
            const maxRange = Math.max(latRange, lonRange);
            const zoom = maxRange > 0 ? Math.max(2, 10 - Math.log2(maxRange * 100)) : 10;

            const map = L.map('map').setView([avgLat, avgLon], zoom);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            }).addTo(map);

            validLocations.forEach(loc => {
                L.marker([loc.latitude, loc.longitude])
                    .addTo(map)
                    .bindPopup(`<b>${loc.name}</b><br>Predictions: ${loc.prediction_count}`);
            });
            window.locationMap = map; // Store map globally for table interaction
        } else {
            const map = L.map('map').setView([-1.2833, 36.8172], 10);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            }).addTo(map);
            window.locationMap = map;
        }
    }

    // Predictions per Location Bar Chart
    if (predictionChartData && predictionChartData.labels && predictionChartData.labels.length > 0) {
        new Chart(document.getElementById('predictionChart'), {
            type: 'bar',
            data: {
                labels: predictionChartData.labels,
                datasets: [{
                    label: 'Number of Predictions',
                    data: predictionChartData.counts,
                    backgroundColor: 'rgba(74, 222, 128, 0.6)',
                    borderColor: 'rgba(74, 222, 128, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: 'Predictions' } },
                    x: { title: { display: true, text: 'Location' } }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    // Crop Distribution Pie Chart
    if (cropChartData && cropChartData.labels && cropChartData.labels.length > 0) {
        new Chart(document.getElementById('cropChart'), {
            type: 'pie',
            data: {
                labels: cropChartData.labels,
                datasets: [{
                    data: cropChartData.counts,
                    backgroundColor: getColors(cropChartData.labels.length)
                }]
            },
            options: {
                plugins: {
                    legend: { position: 'right' }
                }
            }
        });
    }

    // Soil Nutrients Scatter Plot
    if (soilChartData && soilChartData.length > 0) {
        new Chart(document.getElementById('soilChart'), {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'Soil Nutrients (N vs P, colored by K)',
                    data: soilChartData.map(item => ({
                        x: item.nitrogen,
                        y: item.phosphorus,
                        r: Math.min(item.potassium / 50, 20),
                        location: item.location
                    })),
                    backgroundColor: soilChartData.map(item => 
                        `rgba(59, 130, 246, ${Math.min(item.potassium / 500, 0.8)})`)
                }]
            },
            options: {
                scales: {
                    x: { title: { display: true, text: 'Nitrogen (ppm)' } },
                    y: { title: { display: true, text: 'Phosphorus (ppm)' } }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const item = context.raw;
                                return `${item.location}: N=${item.x.toFixed(1)}, P=${item.y.toFixed(1)}, K=${(item.r * 50).toFixed(1)} ppm`;
                            }
                        }
                    }
                }
            }
        });
    }

    // Table Sorting and Map Interaction
    if (summaryData && summaryData.length > 0) {
        const table = document.getElementById('locationTable');
        const headers = table.querySelectorAll('th.sortable');
        let sortDirection = {};

        headers.forEach(header => {
            header.addEventListener('click', () => {
                const sortKey = header.dataset.sort;
                const isAsc = !sortDirection[sortKey];
                sortDirection[sortKey] = isAsc;

                const tbody = table.querySelector('tbody');
                const rows = Array.from(tbody.querySelectorAll('tr'));

                rows.sort((a, b) => {
                    let aValue = a.querySelector(`td:nth-child(${Array.from(headers).indexOf(header) + 1})`).textContent;
                    let bValue = b.querySelector(`td:nth-child(${Array.from(headers).indexOf(header) + 1})`).textContent;

                    if (sortKey === 'latitude' || sortKey === 'longitude' || sortKey === 'prediction_count') {
                        aValue = parseFloat(aValue) || 0;
                        bValue = parseFloat(bValue) || 0;
                        return isAsc ? aValue - bValue : bValue - aValue;
                    } else {
                        return isAsc ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
                    }
                });

                tbody.innerHTML = '';
                rows.forEach(row => tbody.appendChild(row));
            });
        });

        const rows = table.querySelectorAll('tr.clickable');
        rows.forEach(row => {
            row.addEventListener('click', () => {
                const lat = parseFloat(row.dataset.lat);
                const lon = parseFloat(row.dataset.lon);
                if (window.locationMap && !isNaN(lat) && !isNaN(lon)) {
                    window.locationMap.setView([lat, lon], 12);
                }
            });
        });
    }
}