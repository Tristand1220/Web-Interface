# Central dashboard that runs on laptop to monitor raspberry pi devices

from flask import Flask, render_template, jsonify
import requests
import threading
import time

app = Flask(__name__)

#Global storage for discovered devices
discovered_devices = {}
device_health_data = {}
discovery_lock = threading.Lock()

def scan_for_devices():
    # Continously scan for EweGo devices
    
    from scan_network import scan_network
    
    while True:
        try:
            print(f"Scanning for devices...")
            devices = scan_network(max_workers=50)
            
            with discovery_lock:
                # Update discovered devices
                discovered_devices.clear()
                for device in devices:
                    device_id= device['device_id']
                    discovered_devices[device_id] = {
                        'ip': device['ip'],
                        'url': f"http://{device['ip']}:5000",
                        'device_name': device['device_name']
                    }
                if devices:
                    print(f"Found {len(devices)} devices(s)")
                else:
                    print("No devices found")
        except Exception as e:
            print(f"Discovery error: {e}")
            
        # Scan every 30 seconds
        time.sleep(30)
def poll_device_health():
    # Polls all devices for health data
    
    while True:
        with discovery_lock:
            devices_to_poll = dict(discovered_devices)
            
        for device_id, device_info in devices_to_poll.items():
            try:
                url = f"{device_info['url']}/api/health"
                response = requests.get(url, timeout=3)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    with discovery_lock:
                        device_health_data[device_id] = {
                            'status': 'online',
                            'data': data,
                            'last_updated': time.time()
                        }
                else:
                    with discovery_lock:
                        device_health_data[device_id] = {
                            'status': 'error',
                            'data': None,
                            'last_updated': time.time()
                        }
            except Exception as e:
                with discovery_lock:
                    device_health_data[device_id] = {
                        'status': 'offline',
                        'data': None,
                        'last_updated': time.time()
                    }
        # Poll every 2 seconds
        time.sleep(2)
    


# ============================================================================
# FLASK ROUTES 
# ============================================================================

@app.route('/')
def dashboard():  
    return render_template('dashboard.html')

@app.route('/api/devices')
def get_devices():
    
    #Returns all discovered devices and their health data
    with discovery_lock:
        devices_list= []
        for device_id, device_info in discovered_devices.items():
            
            health = device_health_data.get(device_id, {
                'status': 'unknown',
                'data': None,
                'last_seen': 0
            })
            
            devices_list.append({
                'device_id': device_id,
                'device_name': device_info['device_name'],
                'ip': device_info['ip'],
                'url': device_info['url'],
                'status': health['status'],
                'health': health['data'],
                'last_seen': health['last_seen']
            })
    
    return jsonify({
        'devices': devices_list,
        'count': len(devices_list)
    })
    
# Start the recording of the devices from dashboard
@app.route('/api/device/<device_id>/toggle_recording', methods=['POST'])
def toggle_recording(device_id):
    global recording_state
    recording_state = not recording_state
    
    # Call the dual_camera script from here
    
    return jsonify({
        'recording': recording_state,
        'message': 'Recording started' if recording_state else 'Recording stopped'
    })
    
if __name__ == '__main__':
    print("=" * 60)
    print("EweGo Dashboard Starting...")
    print("=" * 60)
    print("\nThis dashboard monitors ALL Raspberry Pi devices")
    print()
    
    # Start background threads
    print("Starting device discovery thread...")
    discovery_thread = threading.Thread(target=scan_for_devices, daemon=True)
    discovery_thread.start()
    
    print("Starting health polling thread...")
    health_thread = threading.Thread(target=poll_device_health, daemon=True)
    health_thread.start()
    
    print("\nStarting web server...")
    print("   Access dashboard at: http://localhost:5000")
    print("\n   Press Ctrl+C to stop")
    print("=" * 60)
    print()
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)