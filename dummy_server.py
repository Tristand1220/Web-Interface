"""
Mock Test Server for EweGoUI Dashboard
Simulates realistic sensor data without requiring actual hardware
Run this instead of app.py to test UI
"""

from flask import Flask, render_template, jsonify
from datetime import datetime
import random
import time
import math

app = Flask(__name__)

# Global state for simulated data
recording_state = False
sync_state = {
    'status': 'synced',
    'last_sync': None,
    'pending_files': 0
}

# Simulation parameters
start_time = time.time()
battery_start = 85.0  # Start at 85%
gps_fix_time = None  # When GPS gets fix

def simulate_gps_data():
    """Simulate GPS acquiring fix and drifting slightly"""
    global gps_fix_time
    
    current_time = time.time()
    elapsed = current_time - start_time
    
    # Simulate GPS taking 30-60 seconds to get first fix
    if elapsed < 45:
        return {
            'connected': True,
            'fix': 'no fix',
            'satellites': min(int(elapsed / 5), 8),  # Gradually acquire satellites
            'latitude': 0.0,
            'longitude': 0.0,
            'altitude': 0.0,
            'available': True
        }
    else:
        # GPS has fix - simulate slight drift (like real GPS)
        if gps_fix_time is None:
            gps_fix_time = current_time
        
        time_since_fix = current_time - gps_fix_time
        
        # Base coordinates (adjust to your location for realism)
        base_lat = 33.7490  # Atlanta, GA area
        base_lon = -84.3880
        
        # Add small random drift (realistic GPS jitter)
        lat_drift = math.sin(time_since_fix / 10) * 0.00001
        lon_drift = math.cos(time_since_fix / 10) * 0.00001
        
        return {
            'connected': True,
            'fix': '3D',
            'satellites': random.randint(10, 15),
            'latitude': base_lat + lat_drift,
            'longitude': base_lon + lon_drift,
            'altitude': 320.5 + random.uniform(-1, 1),
            'available': True
        }

def simulate_battery_data():
    """Simulate battery draining when recording, charging when not"""
    global battery_start, recording_state
    
    elapsed_hours = (time.time() - start_time) / 3600
    
    if recording_state:
        # Drain 5% per hour when recording
        level = battery_start - (elapsed_hours * 5)
        status = 'discharging'
    else:
        # Charge 10% per hour when not recording
        level = min(100, battery_start + (elapsed_hours * 10))
        status = 'charging' if level < 100 else 'full'
    
    level = max(0, min(100, level))
    
    return {
        'level': int(level),
        'status': status,
        'voltage': 11.8 + (level / 100 * 0.8),  # 11.8V to 12.6V range
        'available': True
    }

def simulate_system_metrics():
    """Simulate realistic system metrics with variation"""
    
    elapsed = time.time() - start_time
    
    # CPU usage varies with "load"
    base_cpu = 25
    cpu_spike = math.sin(elapsed / 20) * 15  # Periodic spikes
    cpu_usage = base_cpu + cpu_spike + random.uniform(-5, 5)
    cpu_usage = max(5, min(95, cpu_usage))
    
    # Memory usage slowly increases
    memory_base = 2.1
    memory_growth = (elapsed / 3600) * 0.1  # Grows 0.1GB per hour
    memory_used = memory_base + memory_growth + random.uniform(-0.05, 0.05)
    memory_total = 4.0
    memory_percent = (memory_used / memory_total) * 100
    
    # Disk usage stays relatively stable
    disk_used = 12.8 + random.uniform(-0.1, 0.1)
    disk_total = 32.0
    disk_percent = (disk_used / disk_total) * 100
    
    # Network latency varies
    if random.random() > 0.9:  # 10% chance of spike
        latency = random.uniform(50, 200)
        network_status = 'online'
    else:
        latency = random.uniform(10, 40)
        network_status = 'online'
    
    # CPU temperature correlates with usage
    cpu_temp = 45 + (cpu_usage / 100 * 30) + random.uniform(-2, 2)
    
    # Uptime
    uptime_hours = int(elapsed / 3600)
    
    return {
        'cpu_usage': round(cpu_usage, 1),
        'cpu_temp': round(cpu_temp, 1),
        'memory_used': round(memory_used, 2),
        'memory_total': round(memory_total, 2),
        'memory_percent': round(memory_percent, 1),
        'disk_used': round(disk_used, 2),
        'disk_total': round(disk_total, 2),
        'disk_percent': round(disk_percent, 1),
        'latency': round(latency, 1),
        'network_status': network_status,
        'uptime_hours': uptime_hours
    }

def simulate_sync_status():
    """Simulate sync status based on recording state"""
    global sync_state, recording_state
    
    if recording_state:
        # While recording, files pile up
        sync_state['pending_files'] = random.randint(5, 20)
        sync_state['status'] = 'pending'
    else:
        # When not recording, occasionally sync
        if random.random() > 0.95:  # 5% chance to trigger sync
            sync_state['status'] = 'syncing'
            sync_state['pending_files'] = max(0, sync_state['pending_files'] - 1)
        elif sync_state['pending_files'] > 0:
            sync_state['status'] = 'pending'
        else:
            sync_state['status'] = 'synced'
            sync_state['last_sync'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    return sync_state

@app.route('/')
def dashboard():
    """Serve the dashboard"""
    return render_template('dashboard.html')

@app.route('/api/health')
def health():
    """Return simulated health data matching the expected format"""
    try:
        system_metrics = simulate_system_metrics()
        battery = simulate_battery_data()
        gps = simulate_gps_data()
        sync = simulate_sync_status()
        
        health_data = {
            'device_name': 'RPi CM4 - Sensor System (SIMULATION)',
            
            # System metrics
            'cpu_usage': system_metrics['cpu_usage'],
            'cpu_temp': system_metrics['cpu_temp'],
            'memory_used': system_metrics['memory_used'],
            'memory_total': system_metrics['memory_total'],
            'memory_percent': system_metrics['memory_percent'],
            'disk_used': system_metrics['disk_used'],
            'disk_total': system_metrics['disk_total'],
            'disk_percent': system_metrics['disk_percent'],
            'latency': system_metrics['latency'],
            'network_status': system_metrics['network_status'],
            'uptime_hours': system_metrics['uptime_hours'],
            
            # Sensor data
            'battery': battery,
            'gps': gps,
            'sync': sync,
            'recording': recording_state,
            
            # Metadata
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify(health_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/toggle_recording', methods=['POST'])
def toggle_recording():
    """Toggle recording state"""
    global recording_state
    recording_state = not recording_state
    
    return jsonify({
        'recording': recording_state,
        'message': 'Recording started' if recording_state else 'Recording stopped'
    })

@app.route('/api/sync', methods=['POST'])
def trigger_sync():
    """Simulate manual sync"""
    global sync_state
    
    sync_state['status'] = 'syncing'
    
    # Simulate sync completing after 2 seconds
    import threading
    def complete_sync():
        time.sleep(2)
        sync_state['status'] = 'synced'
        sync_state['pending_files'] = 0
        sync_state['last_sync'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    threading.Thread(target=complete_sync, daemon=True).start()
    
    return jsonify({
        'success': True,
        'message': 'Sync started',
        'sync': sync_state
    })

if __name__ == '__main__':
    print("=" * 60)
    print("🧪 MOCK TEST SERVER RUNNING")
    print("=" * 60)
    print("This server simulates realistic sensor data for testing.")
    print("\nSimulated behaviors:")
    print("  • GPS takes ~45 seconds to acquire fix")
    print("  • Battery drains when recording, charges when not")
    print("  • CPU/Memory usage varies realistically")
    print("  • Network latency has occasional spikes")
    print("  • Sync status changes based on recording state")
    print("\nAccess dashboard at: http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()
    
    app.run(host='0.0.0.0', port=5000, debug=True)