# app.py
import os
import json
import glob
import time 
import psutil
import subprocess
import threading
import socket
import board
import adafruit_max1704x

from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from datetime import datetime
from serial import Serial
from pyubx2 import UBXReader
from mdns_setup import EweGoMDNS

app = Flask(__name__)

# Device mDNS setup
#ID
DEVICE_ID = os.environ.get('DEVICE_ID', socket.gethostname())
DEVICE_NAME = os.environ.get('DEVICE_NAME', f'RaspberryPi - {DEVICE_ID}')

#Service
mdns_setup = None

# Global states
recording_state = False
sync_state = {
    'status': 'synced', # Can either be synced, synching, error, or offline
    'last_sync':None,
    'pending_files':0 # May not need this, will ask for clarifcation
}

gps_data = {
    'connected': False,
    'fix': 'error',
    'latitude': 0.0,
    'longitude': 0.0,
    'altitude': 0.0,
    'available': False
}

#GPS Globals
gps_serial = None
gps_reader = None
gps_thread = None
gps_running = False

# Battery globals
max17_sensor = None
battery_initialized = False

# ============================================================================
# BATTERY MONITORING - MAX17048
# ============================================================================

def init_battery():
    # Intialized battery over I2C
    global max17_sensor, battery_initialized
    
    try:
        i2c = board.I2C()
        max17_sensor = adafruit_max1704x.MAX17048(i2c)
        
        print("Battery monitoring initialized successfully")
        battery_initialized = True
        return True
    
    except Exception as e:
        print(f"Battery initilaized failed: {e}")
        battery_initialized = False
        return False



def get_battery_level():
    #Get battery level
    
    global max17_sensor, battery_initialized
    
    #Initialize battery on the first call
    if not battery_initialized:
        init_battery()
        
    # No battery - return error info
    if not battery_initialized or max17_sensor is None:
        return{
            'level': 0,
            'status': 'unavailable',
            'voltage': 0.0,
            'available': False
        }
    try:
        # Read from battery monitor
        battery_percent = max17_sensor.cell_percentage
        battery_voltage = max17_sensor.cell_voltage
        
        # Charging status
        if battery_percent >= 99 and battery_voltage >= 4.15:
            status = 'full'
        elif battery_voltage >= 4.1:
            status = 'charging'
        elif battery_percent >= 95 and battery_voltage >= 3.9:
            status = 'charging'
        else:
            status = 'discharging'
            
        return {
            'level': int(battery_percent),
            'status': status,
            'voltage': round(battery_voltage, 2),
            'available': True
        }
    except Exception as e:
        print(f"Battery read error: {e}")
        return{
            'level': 0,
            'status': 'unavailable',
            'voltage': 0.0,
            'available': False
        }
        
# ============================================================================
# GPS MONITORING - ZED-X20P
# ============================================================================

def init_gps(port='/dev/ttyACM0', baudrate=38400):
#Initialize GPS serial connection

    global gps_serial,gps_reader, gps_thread, gps_running
    try:
        # Opening the serial connection to GPS
        gps_serial = Serial(port, baudrate, timeout=1)
        
        # UBX Reader, handles UBX and NMEA messages
        gps_reader =UBXReader(gps_serial, protfilter=7)
        
        #Start GPS reading thread
        gps_running=True
        gps_thread = threading.Thread(target=gps_read_threading, daemon=True)
        gps_thread.start()
        
        print("GPS initialized successfully")
        return True
        
    except Exception as e:
        print(f"GPS initilization error: {e}")
        return False
    
def gps_read_threading():
    # Contiously parses through GPS messages
    global gps_data, gps_reader, gps_running
    
    while gps_running:
        try:
            if gps_reader:
                # Read the next message from GPS
                raw_data, parsed_data = gps_reader.read()
                
                if parsed_data:
                    # Update GPS data biased on message type
                    process_gps_message(parsed_data)
                    gps_data['connected']= True
                    gps_data['available'] = True
                    gps_data['last_update'] = time.time()
                    
        except Exception as e:
            if 'timeout' not in str(e).lower():
                print(f"GPS read error: {e}")
            time.sleep(0.1)
            
        # Small delay to prevent CPU spinning
        time.sleep(0.01)
        
def process_gps_message(msg):
    
    # Process incoming GPS message and update global state
    
    global gps_data
    
    try:
        # Get message identity (e.g., 'NAV-PVT', 'GGA', etc.)
        msg_id = str(msg.identity) if hasattr(msg, 'identity') else str(msg.msgID)
        
        # UBX NAV-PVT (Position Velocity Time) - Most comprehensive message
        if 'NAV-PVT' in msg_id:
            gps_data['latitude'] = getattr(msg, 'lat', 0) / 1e7  # Convert to degrees
            gps_data['longitude'] = getattr(msg, 'lon', 0) / 1e7
            gps_data['altitude'] = getattr(msg, 'hMSL', 0) / 1000.0  # Convert to meters
            gps_data['satellites'] = getattr(msg, 'numSV', 0)
            #gps_data['speed'] = getattr(msg, 'gSpeed', 0) / 1000.0  # Convert to m/s
            #gps_data['heading'] = getattr(msg, 'headMot', 0) / 1e5
            
            # Determine fix type
            fix_type = getattr(msg, 'fixType', 0)
            if fix_type == 0:
                gps_data['fix'] = 'no fix'
            elif fix_type == 2:
                gps_data['fix'] = '2D'
            elif fix_type == 3:
                gps_data['fix'] = '3D'
            elif fix_type >= 4:
                gps_data['fix'] = '3D+RTK'  # RTK fix
                
        # UBX NAV-SAT (Satellite Information)
        elif 'NAV-SAT' in msg_id:
            gps_data['satellites'] = getattr(msg, 'numSvs', 0)
            
        # UBX NAV-DOP (Dilution of Precision)
        #elif 'NAV-DOP' in msg_id:
            #gps_data['hdop'] = getattr(msg, 'hDOP', 9999) / 100.0
            
        # NMEA GGA (Global Positioning System Fix Data)
        elif 'GGA' in msg_id:
            gps_data['latitude'] = getattr(msg, 'lat', 0.0)
            gps_data['longitude'] = getattr(msg, 'lon', 0.0)
            gps_data['altitude'] = getattr(msg, 'alt', 0.0)
            gps_data['satellites'] = getattr(msg, 'numSV', 0)
            
            # NMEA quality indicator
            quality = getattr(msg, 'quality', 0)
            if quality == 0:
                gps_data['fix'] = 'no fix'
            elif quality == 1:
                gps_data['fix'] = '3D'
            elif quality in [4, 5]:
                gps_data['fix'] = '3D+RTK'
                
        # NMEA RMC (Recommended Minimum)
        elif 'RMC' in msg_id:
            gps_data['latitude'] = getattr(msg, 'lat', 0.0)
            gps_data['longitude'] = getattr(msg, 'lon', 0.0)
            #gps_data['speed'] = getattr(msg, 'spd', 0.0) * 0.514444  # knots to m/s
            #gps_data['heading'] = getattr(msg, 'cog', 0.0)
            
    except Exception as e:
        print(f"Error processing GPS message {msg_id}: {e}")
        
def get_gps_status():
    #Get GPS status
    
    global gps_data
    
    # Check if GPS data is older than 5 seconds, then update
    if gps_data['last_update']:
        age = time.time() - gps_data['last_update']
        if age > 5:
            gps_data['connected'] = False
            gps_data['fix'] = 'no fix'
        
            
        return {
            # Real data
            'connected': gps_data['connected'],
            'fix': gps_data['fix'],
            'latitude': round(gps_data['latitude'], 6),
            'longitude': round(gps_data['longitude'], 6),
            'altitude': round(gps_data['altitude'], 2),
            'available': gps_data['available']  
        }

# ============================================================================
# SYNC STATUS
# ============================================================================

def check_sync_status():
    #Check sync status from remote server
    global sync_state
    
    try:
        # Check for pending files
        recording_path = '/home/{user}/recordings/'
        
        if os.path.exists(recording_path):
            # Counting files needed to be synced
            all_files = [f for f in os.listdir(recording_path)
                         if os.path.isfile(os.path.join(recording_path, f))
                         and not f.endswith('.synced')]
            sync_state['pending_files']= len(all_files)
            
            # If network stable, files will sync
            try:
                subprocess.check_output(['ping', '-c', '1', '8.8.8.8'], timeout=2)
                if sync_state['pending_files'] > 0:
                    # Reaming synching as long as there are files
                    sync_state['status'] = 'pending'
                else:
                    # Complete sync once now files are left
                    sync_state['status'] = 'synced'
                    if sync_state['last_sync'] is None:
                        sync_state['last_sync'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            except:
                # Can't sync while offline
                sync_state['status'] = 'offline'
        else:
            # Creating recording directory if none exists
            os.makedirs(recording_path, exist_ok=True)
            sync_state['status'] = 'synced'
            sync_state['pending_files'] = 0
            
    except Exception as e:
        print(f"Sync check error: {e}")
        sync_state['status'] = 'error'
        
    return sync_state
            
# ============================================================================
# SYSTEM METRICS
# ============================================================================
def get_system_metrics():
    # Comphrensive system status
    
    # Memory Usage
    memory = psutil.virtual_memory()
    memory_used_gb = memory.used / (1024**3)
    memory_total_gb = memory.total / (1024**3)
    memory_percent = memory.percent
    
    # Uptime - find how long the system has been running
    try:
        uptime_sec = int(subprocess.check_output(['cat', '/proc/uptime']).decode().split()[0].split('.')[0])
        uptime_hrs = uptime_sec // 3600
    except:
        uptime_hrs = 0
        
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
    sync = check_sync_status()
    
    return {
        'device_name': 'RPi CM4 - Sensor System',
        'memory_used': round(memory_used_gb, 2),
        'memory_total': round(memory_total_gb, 2),
        'memory_percent': round(memory_percent, 1),
        'latency': round(latency, 1),
        'network_status': network_status,
        'uptime_hrs': uptime_hrs,
        'recording': recording_state,
        'battery': battery,
        'gps': gps,
        'sync': sync,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
# ============================================================================
# FLASK ROUTES 
# ============================================================================

@app.route('/')
def dashboard():  
    return render_template('dashboard.html')

# Collect system metrics (health) data as a JSON from API
@app.route('/api/health')
def health():
    try:
        health_data = get_system_metrics()
        return jsonify(health_data)
    except Exception as e:
        print(f"Health API error: {e}")
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
    })

"""# Triggering a sync from dashboard (need to complete)
@app.route('/api/sync', methods=['POST'])
def trigger_sync():"""

if __name__ == '__main__':
    print("=" * 60)
    print("EweGo Pi App Starting...")
    print("=" * 60)
    print(f"\nDevice ID: {DEVICE_ID}")
    print(f"Device Name: {DEVICE_NAME}")
    
    # Initialize mDNS service
    print("\Starting mDNS service...")
    mdns_service = EweGoMDNS(device_id=DEVICE_ID, port=5000)
    if mdns_service.start():
        print(f"Device discoverable at: http://{DEVICE_ID}.local:5000")
    else:
        print("mDNS failed - device only accessible by IP address")
    
    # Initialize GPS
    print("\Initializing GPS...")
    if init_gps():
        print("GPS initialized (waiting for fix...)")
    else:
        print("GPS initialization failed")
    
    # Create recordings directory
    os.makedirs('/home/pi/recordings', exist_ok=True)
    print("\nRecordings directory ready")
    
    print("\nStarting Flask web server...")
    print(f"   Local: http://localhost:5000")
    print(f"   Network: http://{DEVICE_ID}.local:5000")
    print("\n   Press Ctrl+C to stop")
    print("=" * 60)
    print()
    
    try:
        # Run Flask app
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        # Clean shutdown
        if mdns_service:
            mdns_service.stop()
        print("✅ Shutdown complete")