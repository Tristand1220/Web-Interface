#!/usr/bin/env python3
"""
Network Scanner for EweGoUI Devices
Works in WSL where mDNS discovery doesn't work
Scans network for devices responding to /api/health endpoint
"""

import requests
import socket
import subprocess
import concurrent.futures
from ipaddress import IPv4Network

def get_local_network():
    """
    Get the local network range to scan
    
    Returns:
        str: Network in CIDR notation (e.g., '192.168.1.0/24')
    """
    try:
        # Get default gateway
        result = subprocess.run(['ip', 'route'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'default' in line:
                gateway = line.split()[2]
                # Extract network portion (assume /24)
                network_parts = gateway.split('.')
                network = f"{'.'.join(network_parts[:3])}.0/24"
                return network
    except:
        pass
    
    # Fallback: common private networks
    return '192.168.1.0/24'

def check_device(ip):
    """
    Check if an IP is an EweGoUI device
    
    Args:
        ip: IP address to check
    
    Returns:
        dict or None: Device info if EweGoUI device found, None otherwise
    """
    try:
        # Try to connect to the health API
        url = f"http://{ip}:5000/api/health"
        response = requests.get(url, timeout=1)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if it's an EweGoUI device by looking for expected fields
            if 'device_id' in data or 'device_name' in data:
                return {
                    'ip': ip,
                    'device_id': data.get('device_id', 'unknown'),
                    'device_name': data.get('device_name', 'Unknown Device'),
                    'battery': data.get('battery', {}).get('level', 'N/A'),
                    'gps': data.get('gps', {}).get('fix', 'unknown'),
                    'recording': data.get('recording', False),
                    'network_status': data.get('network_status', 'unknown')
                }
    except:
        pass
    
    return None

def scan_network(network_range=None, max_workers=50):
    """
    Scan network for EweGoUI devices
    
    Args:
        network_range: Network to scan in CIDR notation (e.g., '192.168.1.0/24')
        max_workers: Number of concurrent threads for scanning
    
    Returns:
        list: List of discovered devices
    """
    if network_range is None:
        network_range = get_local_network()
    
    print("=" * 60)
    print("🔍 EweGoUI Network Scanner")
    print("=" * 60)
    print(f"\nScanning network: {network_range}")
    print(f"Looking for devices on port 5000...")
    print(f"This may take 30-60 seconds...\n")
    
    devices = []
    network = IPv4Network(network_range)
    total_ips = network.num_addresses
    
    # Scan IPs concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all IP checks
        future_to_ip = {
            executor.submit(check_device, str(ip)): str(ip) 
            for ip in network.hosts()
        }
        
        # Collect results
        completed = 0
        for future in concurrent.futures.as_completed(future_to_ip):
            completed += 1
            if completed % 50 == 0:
                print(f"  Scanned {completed}/{total_ips} addresses...")
            
            result = future.result()
            if result:
                devices.append(result)
                print(f"\n✅ Found device: {result['device_id']}")
                print(f"   IP: {result['ip']}")
                print(f"   Name: {result['device_name']}")
                print(f"   URL: http://{result['ip']}:5000\n")
    
    return devices

def print_summary(devices):
    """Print summary of discovered devices"""
    print("\n" + "=" * 60)
    print("📊 Scan Summary")
    print("=" * 60)
    
    if not devices:
        print("\n❌ No EweGoUI devices found on the network")
        print("\nTroubleshooting:")
        print("1. Make sure Raspberry Pi is powered on")
        print("2. Make sure it's running app.py")
        print("3. Check both devices are on same network")
        print("4. Try accessing directly: http://<pi-ip>:5000")
        print("5. Check firewall isn't blocking port 5000")
        return
    
    print(f"\n✅ Found {len(devices)} device(s):\n")
    
    for device in devices:
        print(f"📱 {device['device_id']}")
        print(f"   Name: {device['device_name']}")
        print(f"   IP: {device['ip']}")
        print(f"   Dashboard: http://{device['ip']}:5000")
        print(f"   Health API: http://{device['ip']}:5000/api/health")
        print(f"   Battery: {device['battery']}%")
        print(f"   GPS: {device['gps']}")
        print(f"   Recording: {'🔴 Yes' if device['recording'] else '⚪ No'}")
        print()

def save_devices_to_file(devices, filename='discovered_devices.txt'):
    """Save discovered devices to a file"""
    if not devices:
        return
    
    with open(filename, 'w') as f:
        f.write("EweGoUI Discovered Devices\n")
        f.write("=" * 60 + "\n\n")
        
        for device in devices:
            f.write(f"Device ID: {device['device_id']}\n")
            f.write(f"Name: {device['device_name']}\n")
            f.write(f"IP: {device['ip']}\n")
            f.write(f"URL: http://{device['ip']}:5000\n")
            f.write(f"Battery: {device['battery']}%\n")
            f.write(f"GPS: {device['gps']}\n")
            f.write(f"Recording: {'Yes' if device['recording'] else 'No'}\n")
            f.write("\n")
    
    print(f"📝 Device list saved to: {filename}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Scan network for EweGo devices (WSL-compatible)')
    parser.add_argument('-n', '--network', type=str, 
                       help='Network to scan (e.g., 192.168.1.0/24)')
    parser.add_argument('-w', '--workers', type=int, default=50,
                       help='Number of concurrent workers (default: 50)')
    parser.add_argument('-s', '--save', action='store_true',
                       help='Save discovered devices to file')
    args = parser.parse_args()
    
    # Scan network
    devices = scan_network(network_range=args.network, max_workers=args.workers)
    
    # Print summary
    print_summary(devices)
    
    # Optionally save to file
    if args.save and devices:
        save_devices_to_file(devices)
    
    print("\n" + "=" * 60)
    print("✅ Scan complete!")
    print("=" * 60)