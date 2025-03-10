#!/bin/bash

# Template for creating HTML templates
# This script is called by the main install_ubuntu_server.sh script

create_html_templates() {
    local install_dir=$1
    
    # Create SLAM and path planning visualization templates
    mkdir -p "${install_dir}/web/templates/additional"
    
    log "Creating SLAM map template..."
    cat > "${install_dir}/web/templates/additional/slam_map.html" << EOF
{% extends "layout.html" %}

{% block title %}SLAM Map{% endblock %}

{% block content %}
<div class="container mt-4">
    <h1>SLAM Map Visualization</h1>
    
    <div class="row mb-4">
        <div class="col-md-12">
            <div class="card">
                <div class="card-header">
                    <h5>Current SLAM Map</h5>
                </div>
                <div class="card-body text-center">
                    <img id="slam-map" src="/api/slam_map/latest" class="img-fluid" alt="SLAM Map">
                </div>
                <div class="card-footer">
                    <button id="refresh-map" class="btn btn-primary">Refresh Map</button>
                </div>
            </div>
        </div>
    </div>
    
    <div class="row">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h5>Robot Position</h5>
                </div>
                <div class="card-body">
                    <p><strong>X:</strong> <span id="robot-x">0.0</span> m</p>
                    <p><strong>Y:</strong> <span id="robot-y">0.0</span> m</p>
                    <p><strong>Heading:</strong> <span id="robot-heading">0.0</span>°</p>
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h5>Map Statistics</h5>
                </div>
                <div class="card-body">
                    <p><strong>Map Resolution:</strong> <span id="map-resolution">0.05</span> m/pixel</p>
                    <p><strong>Map Size:</strong> <span id="map-size">100.0</span> m</p>
                    <p><strong>Detected Obstacles:</strong> <span id="obstacle-count">0</span></p>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
    $(document).ready(function() {
        // Refresh map button
        $('#refresh-map').click(function() {
            $('#slam-map').attr('src', '/api/slam_map/latest?' + new Date().getTime());
        });
        
        // Request regular status updates
        const socket = io();
        socket.on('connect', function() {
            socket.emit('request_status_update');
        });
        
        socket.on('status_update', function(data) {
            // Update robot position display
            $('#robot-x').text(data.position.x.toFixed(2));
            $('#robot-y').text(data.position.y.toFixed(2));
            $('#robot-heading').text(data.position.theta.toFixed(2));
        });
        
        // Request updates every 5 seconds
        setInterval(function() {
            socket.emit('request_status_update');
        }, 5000);
    });
</script>
{% endblock %}
EOF

    log "Creating path planning template..."
    cat > "${install_dir}/web/templates/additional/path_planning.html" << EOF
{% extends "layout.html" %}

{% block title %}Path Planning{% endblock %}

{% block content %}
<div class="container mt-4">
    <h1>Path Planning</h1>
    
    <div class="row mb-4">
        <div class="col-md-12">
            <div class="card">
                <div class="card-header">
                    <h5>Mowing Zones</h5>
                </div>
                <div class="card-body">
                    <div id="zones-map" style="height: 400px; background-color: #f5f5f5; position: relative;">
                        <canvas id="zones-canvas" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"></canvas>
                    </div>
                </div>
                <div class="card-footer">
                    <button id="refresh-zones" class="btn btn-primary">Refresh Zones</button>
                    <button id="plan-path" class="btn btn-success">Plan Path</button>
                </div>
            </div>
        </div>
    </div>
    
    <div class="row">
        <div class="col-md-12">
            <div class="card">
                <div class="card-header">
                    <h5>Mowing Zones</h5>
                </div>
                <div class="card-body">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Name</th>
                                <th>Pattern</th>
                                <th>Direction</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="zones-table-body">
                            <!-- Zones will be populated here -->
                        </tbody>
                    </table>
                </div>
                <div class="card-footer">
                    <button id="add-zone" class="btn btn-primary">Add Zone</button>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
    $(document).ready(function() {
        // Canvas for drawing zones
        const canvas = document.getElementById('zones-canvas');
        const ctx = canvas.getContext('2d');
        const zonesData = [];
        
        // Set canvas size
        function resizeCanvas() {
            const container = document.getElementById('zones-map');
            canvas.width = container.clientWidth;
            canvas.height = container.clientHeight;
            drawZones();
        }
        
        window.addEventListener('resize', resizeCanvas);
        resizeCanvas();
        
        // Load zones data
        function loadZones() {
            $.getJSON('/api/path_planning/zones', function(data) {
                zonesData.length = 0;
                Array.prototype.push.apply(zonesData, data);
                
                // Update the table
                updateZonesTable();
                
                // Draw zones on canvas
                drawZones();
            });
        }
        
        // Draw zones on canvas
        function drawZones() {
            // Clear canvas
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            if (zonesData.length === 0) return;
            
            // Find bounds of all zones
            let minX = Infinity, minY = Infinity;
            let maxX = -Infinity, maxY = -Infinity;
            
            zonesData.forEach(zone => {
                zone.perimeter.forEach(point => {
                    minX = Math.min(minX, point[0]);
                    minY = Math.min(minY, point[1]);
                    maxX = Math.max(maxX, point[0]);
                    maxY = Math.max(maxY, point[1]);
                });
            });
            
            // Add padding
            const padding = 2;
            minX -= padding;
            minY -= padding;
            maxX += padding;
            maxY += padding;
            
            // Calculate scale to fit canvas
            const scaleX = canvas.width / (maxX - minX);
            const scaleY = canvas.height / (maxY - minY);
            const scale = Math.min(scaleX, scaleY);
            
            // Draw each zone
            zonesData.forEach((zone, index) => {
                // Different color for each zone
                const colors = ['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6'];
                const color = colors[index % colors.length];
                
                ctx.beginPath();
                zone.perimeter.forEach((point, i) => {
                    const x = (point[0] - minX) * scale;
                    const y = canvas.height - (point[1] - minY) * scale; // Flip Y axis
                    
                    if (i === 0) {
                        ctx.moveTo(x, y);
                    } else {
                        ctx.lineTo(x, y);
                    }
                });
                
                // Close the path
                if (zone.perimeter.length > 0) {
                    const first = zone.perimeter[0];
                    const x = (first[0] - minX) * scale;
                    const y = canvas.height - (first[1] - minY) * scale;
                    ctx.lineTo(x, y);
                }
                
                ctx.fillStyle = color + '33'; // Add transparency
                ctx.fill();
                ctx.strokeStyle = color;
                ctx.lineWidth = 2;
                ctx.stroke();
                
                // Draw zone name
                if (zone.perimeter.length > 0) {
                    // Find center of zone (average of all points)
                    let centerX = 0, centerY = 0;
                    zone.perimeter.forEach(point => {
                        centerX += point[0];
                        centerY += point[1];
                    });
                    centerX /= zone.perimeter.length;
                    centerY /= zone.perimeter.length;
                    
                    // Convert to canvas coordinates
                    const x = (centerX - minX) * scale;
                    const y = canvas.height - (centerY - minY) * scale;
                    
                    ctx.font = '14px Arial';
                    ctx.fillStyle = '#000';
                    ctx.textAlign = 'center';
                    ctx.fillText(zone.name, x, y);
                }
            });
        }
        
        // Update zones table
        function updateZonesTable() {
            const tbody = document.getElementById('zones-table-body');
            tbody.innerHTML = '';
            
            zonesData.forEach(zone => {
                const row = document.createElement('tr');
                
                // ID
                const idCell = document.createElement('td');
                idCell.textContent = zone.id;
                row.appendChild(idCell);
                
                // Name
                const nameCell = document.createElement('td');
                nameCell.textContent = zone.name;
                row.appendChild(nameCell);
                
                // Pattern
                const patternCell = document.createElement('td');
                patternCell.textContent = zone.pattern.charAt(0).toUpperCase() + zone.pattern.slice(1);
                row.appendChild(patternCell);
                
                // Direction
                const directionCell = document.createElement('td');
                if (zone.direction_degrees !== undefined) {
                    directionCell.textContent = zone.direction_degrees + '°';
                } else {
                    directionCell.textContent = 'N/A';
                }
                row.appendChild(directionCell);
                
                // Actions
                const actionsCell = document.createElement('td');
                const editBtn = document.createElement('button');
                editBtn.className = 'btn btn-sm btn-primary me-2';
                editBtn.textContent = 'Edit';
                editBtn.onclick = function() { editZone(zone.id); };
                actionsCell.appendChild(editBtn);
                
                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'btn btn-sm btn-danger';
                deleteBtn.textContent = 'Delete';
                deleteBtn.onclick = function() { deleteZone(zone.id); };
                actionsCell.appendChild(deleteBtn);
                
                row.appendChild(actionsCell);
                
                tbody.appendChild(row);
            });
        }
        
        // Initialize
        loadZones();
        
        // Button handlers
        $('#refresh-zones').click(function() {
            loadZones();
        });
        
        $('#plan-path').click(function() {
            alert('Path planning would be triggered here!');
        });
        
        $('#add-zone').click(function() {
            alert('Zone creation interface would open here!');
        });
        
        function editZone(id) {
            alert('Edit zone ' + id + ' interface would open here!');
        }
        
        function deleteZone(id) {
            if (confirm('Are you sure you want to delete zone ' + id + '?')) {
                alert('Zone deletion would happen here!');
            }
        }
    });
</script>
{% endblock %}
EOF
}
