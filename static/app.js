let chartCounter = 0;

async function handleFormSubmit(event) {
    event.preventDefault();
    const input = document.getElementById("userInput");
    const question = input.value.trim();
    if (!question) return;

    input.value = "";
    sendQuery(question);
}

function sendPresetQuery(text) {
    sendQuery(text);
}

async function sendQuery(question) {
    const container = document.getElementById("messagesContainer");

    // 1. Render User Message
    const userMsgHtml = `
        <div class="message user-message">
            <div class="avatar">U</div>
            <div class="message-content">
                <p>${escapeHtml(question)}</p>
            </div>
        </div>
    `;
    container.insertAdjacentHTML("beforeend", userMsgHtml);

    // 2. Render Loading Assistant Placeholder
    const loadingId = "loading-" + Date.now();
    const loadingHtml = `
        <div class="message assistant-message" id="${loadingId}">
            <div class="avatar">🌊</div>
            <div class="message-content">
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>
        </div>
    `;
    container.insertAdjacentHTML("beforeend", loadingHtml);
    scrollToBottom();

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: question })
        });

        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }

        const data = await response.json();

        // Update Engine Badge
        if (data.engine) {
            document.getElementById("engineBadge").innerText = `Engine: ${data.engine.toUpperCase()}`;
        }

        // Replace loading message with full response
        const loadingElem = document.getElementById(loadingId);
        if (loadingElem) {
            chartCounter++;
            const chartId = `chart-${chartCounter}`;
            const sqlId = `sql-${chartCounter}`;

            let chartBlock = "";
            if (data.chart_type && data.chart_type !== "none" && data.rows && data.rows.length > 0) {
                chartBlock = `<div id="${chartId}" class="chart-container"></div>`;
            }

            let dataTableBlock = "";
            if (data.rows && data.rows.length > 0) {
                const cols = data.columns || Object.keys(data.rows[0]);
                let tableRows = data.rows.slice(0, 15).map(r => 
                    `<tr>${cols.map(c => `<td>${r[c] !== null ? r[c] : ''}</td>`).join('')}</tr>`
                ).join('');

                dataTableBlock = `
                    <details style="margin-top: 12px;">
                        <summary style="cursor:pointer; font-size:12px; color:var(--text-muted); font-family:var(--font-mono);">
                            📊 View Raw SQL Rows (${data.rows.length} rows returned)
                        </summary>
                        <div class="data-table-wrapper">
                            <table class="data-table">
                                <thead><tr>${cols.map(c => `<th>${c}</th>`).join('')}</tr></thead>
                                <tbody>${tableRows}</tbody>
                            </table>
                        </div>
                    </details>
                `;
            }

            loadingElem.innerHTML = `
                <div class="avatar">🌊</div>
                <div class="message-content">
                    <p>${formatMarkdownText(data.answer)}</p>

                    ${chartBlock}

                    <div class="sql-accordion">
                        <button class="sql-toggle" onclick="toggleSql('${sqlId}')">
                            💻 Executed SQL Query ⚡
                        </button>
                        <pre id="${sqlId}" class="sql-code-block">${escapeHtml(data.sql_query)}</pre>
                    </div>

                    ${dataTableBlock}
                </div>
            `;

            // Render Visualization if present
            if (data.rows && data.rows.length > 0) {
                if (data.chart_type === "depth_profile") {
                    renderDepthProfileChart(chartId, data.rows);
                } else if (data.chart_type === "map") {
                    renderLeafletMap(chartId, data.rows);
                } else if (data.chart_type === "time_series") {
                    renderTimeSeriesChart(chartId, data.rows);
                }
            }
        }
    } catch (err) {
        const loadingElem = document.getElementById(loadingId);
        if (loadingElem) {
            loadingElem.innerHTML = `
                <div class="avatar">🌊</div>
                <div class="message-content" style="border-color: #ff3b30;">
                    <p>⚠️ <strong>Error processing request:</strong> ${escapeHtml(err.message)}</p>
                </div>
            `;
        }
    }
    scrollToBottom();
}

function toggleSql(id) {
    const elem = document.getElementById(id);
    if (elem) {
        elem.style.display = elem.style.display === "block" ? "none" : "block";
    }
}

function scrollToBottom() {
    const container = document.getElementById("messagesContainer");
    container.scrollTop = container.scrollHeight;
}

function escapeHtml(text) {
    if (!text) return "";
    return text.toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function formatMarkdownText(text) {
    if (!text) return "";
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/`([^`]+)`/g, '<code style="background:rgba(255,255,255,0.1); padding:2px 4px; border-radius:4px;">$1</code>');
}

/* Visualization Handlers */

function renderDepthProfileChart(containerId, rows) {
    setTimeout(() => {
        const depths = rows.map(r => r.depth_m);
        const temps = rows.map(r => r.temperature);
        const salinities = rows.map(r => r.salinity).filter(s => s !== undefined);

        const traces = [
            {
                x: temps,
                y: depths,
                mode: 'lines+markers',
                name: 'Temperature (°C)',
                line: { color: '#00f2fe', width: 2.5 },
                marker: { size: 6 }
            }
        ];

        if (salinities.length > 0) {
            traces.push({
                x: salinities,
                y: depths,
                mode: 'lines+markers',
                name: 'Salinity (PSU)',
                xaxis: 'x2',
                line: { color: '#7f00ff', width: 2.5 },
                marker: { size: 6 }
            });
        }

        const layout = {
            title: { text: 'Depth Profile (Inverted Depth)', font: { color: '#f0f6fc', size: 14 } },
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            margin: { l: 50, r: 50, t: 40, b: 40 },
            yaxis: {
                title: 'Depth (m)',
                autorange: 'reversed',  // Invert Depth axis (0 at top)
                color: '#8b9eb7',
                gridcolor: 'rgba(255,255,255,0.08)'
            },
            xaxis: {
                title: 'Temperature (°C)',
                color: '#00f2fe',
                gridcolor: 'rgba(255,255,255,0.08)'
            },
            xaxis2: {
                title: 'Salinity (PSU)',
                color: '#7f00ff',
                overlaying: 'x',
                side: 'top'
            },
            legend: { font: { color: '#f0f6fc' }, orientation: 'h', y: -0.2 }
        };

        Plotly.newPlot(containerId, traces, layout, { responsive: true });
    }, 100);
}

function renderTimeSeriesChart(containerId, rows) {
    setTimeout(() => {
        // Group by float WMO ID if multiple floats present
        const floatGroups = {};
        rows.forEach(r => {
            const wmo = r.wmo_id || "Float";
            if (!floatGroups[wmo]) floatGroups[wmo] = [];
            floatGroups[wmo].push(r);
        });

        const traces = [];
        const colors = ['#00f2fe', '#4facfe', '#7f00ff', '#ff007f', '#00ff66'];
        let colorIdx = 0;

        for (const [wmo, group] of Object.entries(floatGroups)) {
            const yVals = group.map(r => r.salinity !== undefined ? r.salinity : r.temperature);
            const xVals = group.map(r => r.depth_m !== undefined ? r.depth_m : r.profile_date);
            const paramLabel = group[0].salinity !== undefined ? 'Salinity (PSU)' : 'Temp (°C)';

            traces.push({
                x: xVals,
                y: yVals,
                mode: 'lines+markers',
                name: `Float ${wmo} (${paramLabel})`,
                line: { color: colors[colorIdx % colors.length], width: 2.5 },
                marker: { size: 6 }
            });
            colorIdx++;
        }

        const layout = {
            title: { text: 'Salinity / Parameter Comparison', font: { color: '#f0f6fc', size: 14 } },
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            margin: { l: 50, r: 50, t: 40, b: 40 },
            xaxis: { title: 'Depth / Date', color: '#8b9eb7', gridcolor: 'rgba(255,255,255,0.08)' },
            yaxis: { title: 'Value', color: '#8b9eb7', gridcolor: 'rgba(255,255,255,0.08)' },
            legend: { font: { color: '#f0f6fc' }, orientation: 'h', y: -0.2 }
        };

        Plotly.newPlot(containerId, traces, layout, { responsive: true });
    }, 100);
}

function renderLeafletMap(containerId, rows) {
    setTimeout(() => {
        const container = document.getElementById(containerId);
        container.style.height = "380px";

        // Center map around average coordinates or Indian Ocean center
        const avgLat = rows.reduce((sum, r) => sum + (r.latitude || 0), 0) / rows.length || 5.0;
        const avgLon = rows.reduce((sum, r) => sum + (r.longitude || 0), 0) / rows.length || 75.0;

        const map = L.map(containerId).setView([avgLat, avgLon], 4);

        // Dark Matter tiles for ocean aesthetic
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
            maxZoom: 18
        }).addTo(map);

        rows.forEach(r => {
            if (r.latitude && r.longitude) {
                const isBgc = r.is_bgc || (r.max_chlorophyll !== undefined);
                const markerColor = isBgc ? "#00ff66" : "#00f2fe";

                const circle = L.circleMarker([r.latitude, r.longitude], {
                    color: markerColor,
                    fillColor: markerColor,
                    fillOpacity: 0.8,
                    radius: 8
                }).addTo(map);

                const popupHtml = `
                    <div style="font-family:sans-serif; color:#0e1a2e;">
                        <strong style="font-size:14px;">🌊 WMO Float ${r.wmo_id}</strong><br>
                        <b>Region:</b> ${r.region || 'Indian Ocean'}<br>
                        <b>Lat:</b> ${r.latitude}, <b>Lon:</b> ${r.longitude}<br>
                        ${r.last_seen ? `<b>Last Profile:</b> ${r.last_seen}<br>` : ''}
                        ${isBgc ? `<span style="color:#008800; font-weight:bold;">🌿 BGC Enabled</span>` : ''}
                    </div>
                `;
                circle.bindPopup(popupHtml);
            }
        });
    }, 100);
}
