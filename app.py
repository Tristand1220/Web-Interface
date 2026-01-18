# app.py
import os
import json
import glob
import time 
import psutil
import subprocess
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from threading import Lock
from datetime import datetime

app = Flask(__name__)

"""# Global states
recording_state = False
sync_state = {
    'status': 'synced', # Can either be synced, synching, error, or offline
    'last_sync':None,
    'pending_files':0 # May not need this, will ask for clarifcation
}

def get_battery_level():
    #Get battery level
    try:
        # Read from battery monitor
    except Eexception as e:
        return "Error"
    
def get_gps_status():
    #Get GPS status
    
    try:
        # Check if GPS device exist or not
        gps_devices=['/dev/ttyUSB0','/dev/ttyUSB1','/dev/ttyUSB2','/dev/ttyUSB3', '/dev/ttyAMAO','/dev/ttyACMO' ]
        gps_connected = any(os.path.exists(dev) for dev in gps_devices)
        
        if gps_connected:
            # Reads GPS data from sensor
            
            return {
                # Real data
            }
    except Exception as e:
    print(f"GPS read error: {e}")
    return {
        'connected': False,
        'fix': 'error',
        'latitude': 0.0,
        'longitude': 0.0,
        'available': False
    }
            
def get_system_metrics():
    # Comphrensive system status
    
    # Memory Usage
    memory = psutil.virtual_memory()
    memory_used_gb = memory.used / (1024**3)
    memory_total_gb = memory.total / (1024**3)
    memory_percent = memory.percent
    
    #Uptime - find how long the system has been running
    uptime_sec = int(subprocess.check_output(['cat', '/proc/uptime']).decode().split()[0].split('.')[0])
    uptime_hrs = uptime_seconds //3600
    
    
    # Network Latency
    try:
        ping = subprocess.check_output(['ping', '-c', '1', '8.8.8.8'], timeout=2)
        latency = float(ping.decode().split('time=')[1].split(' ms')[0])
        network_status = 'online'
    except:
        latency = 0
        network_status='offline'
        
    # Other monitored data
    battery = get_battery_level()
    gps = get_gps_status()
    
    return {
        'device_name': 'RPi CM4 - Sensor System',
        'memory_used': round(memory_used_gb, 2),
        'memory_total': round(memory_total_gb, 2),
        'memory_percent': round(memory_percent, 1),
        'latency': round(latency, 1),
        'network_status': network_status,
        'battery': battery,
        'gps': gps,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }"""
    

@app.route('/')
def dashboard():  
    return render_template('dashboard.html')

"""# Collect system metrics (health) data as a JSON from API
@app.route('/api/health')
def health():
    try:
        health_data = get_system_metrics()
        return jsonify(health_data)
    except Exception as e:
        return jsonify({'error' : str(e)}), 500
    
# Start the recording of the devices from dashboard
@app.route('/api/toggle_recording', methods=['POST'])
def toggle_recording():
    global recording_state
    recording_state = not recording_state
    
    # Call the dual_camera script from here
    
    return jsonify({
        'recording': recording_state,
        'message': 'Recording started' if recording_state else 'Recording stopped'
    })"""
    


if __name__ == '__main__':
    # Use 0.0.0.0 to make it accessible on the network
    app.run(host='0.0.0.0', port=5000, debug=True)