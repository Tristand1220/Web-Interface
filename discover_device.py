#!/usr/bin/env python3
"""
Scans local network to discover EweGo devices using mDNS.
"""

from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
import time
import socket

class EweGoListener(ServiceListener):
    """Listens for EweGo device announcements"""
    
    def __init__(self):
        self.devices = {}
    
    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when service is removed from network"""
        if name in self.devices:
            print(f"Device offline: {name}")
            del self.devices[name]
    
    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when new device is discovered"""
        info = zc.get_service_info(type_, name)
        if info:
            # Parsing device information
            device_id = info.properties.get(b'device_id', b'unknown').decode('utf-8')
            service_name = info.properties.get(b'service', b'Unknown').decode('utf-8')
            version = info.properties.get(b'version', b'?').decode('utf-8')
            
            # Get IP address
            if info.addresses:
                ip_address = socket.inet_ntoa(info.addresses[0])
            else:
                ip_address = "unknown"
            
            # Store device info
            self.devices[name] = {
                'device_id': device_id,
                'service_name': service_name,
                'version': version,
                'ip': ip_address,  # Changed from 'ip_address' to 'ip'
                'port': info.port,
                'hostname': info.server.rstrip('.')
            }
            
            # Print discovery info
            print(f"\n✅ Found device: {device_id}")
            print(f"   Service: {service_name}")
            print(f"   Hostname: {info.server.rstrip('.')}")
            print(f"   IP: {ip_address}")
            print(f"   Port: {info.port}")
            print(f"   URL: http://{info.server.rstrip('.')}:{info.port}")
            print(f"   API: http://{info.server.rstrip('.')}:{info.port}/api/health")
    
    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when service is updated"""
        pass


def discover_devices(timeout=10):
    """Discover all EweGo devices on network within timeout"""
    
    print("=" * 60)
    print("EweGoUI Device Discovery")
    print("=" * 60)
    print(f"\nScanning for devices (timeout: {timeout}s)...")
    print("Listening for service type: _ewego._tcp.local.")
    print()
    
    zeroconf = Zeroconf()
    listener = EweGoListener()
    browser = ServiceBrowser(zeroconf, "_ewego._tcp.local.", listener)
    
    try:
        time.sleep(timeout)
    except KeyboardInterrupt:
        print("\n\nScan stopped by user")
    finally:
        zeroconf.close()
    
    return listener.devices


def print_summary(devices):
    """Print a summary of discovered devices"""
    print("\n" + "=" * 60)
    print(f"Discovery Summary")
    print("=" * 60)
    
    if not devices:
        print("\nNo EweGo devices found on the network")
        print("\nTroubleshooting:")
        print("1. Make sure Raspberry Pi is powered on and running app.py")
        print("2. Check devices are on the same network")
        print("3. Verify Avahi is running: sudo systemctl status avahi-daemon")
        print("4. Check firewall isn't blocking mDNS (port 5353 UDP)")
        return
    
    print(f"\nFound {len(devices)} device(s):\n")
    
    for name, info in devices.items():
        print(f"{info['device_id']}")
        print(f"   Hostname: {info['hostname']}")
        print(f"   IP Address: {info['ip']}:{info['port']}")
        print(f"   Dashboard: http://{info['hostname']}:{info['port']}")
        print(f"   Health API: http://{info['hostname']}:{info['port']}/api/health")
        print()


def test_device_connection(devices):
    """Test HTTP connection to discovered devices"""
    import requests
    
    print("=" * 60)
    print("Testing Device Connections")
    print("=" * 60)
    print()
    
    for name, info in devices.items():
        print(f"Testing {info['device_id']}...")
        
        # Try hostname first
        url = f"http://{info['hostname']}:{info['port']}/api/health"
        
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"   Connected successfully")
                print(f"   Battery: {data.get('battery', {}).get('level', 'N/A')}%")
                print(f"   GPS: {data.get('gps', {}).get('fix', 'unknown')}")
                print(f"   Recording: {data.get('recording', False)}")
            else:
                print(f"   ⚠️  Connected but got status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Connection failed: {e}")
            
            # Try IP address as fallback
            if info['ip'] != 'unknown':
                print(f"   Trying IP address...")
                url_ip = f"http://{info['ip']}:{info['port']}/api/health"
                try:
                    response = requests.get(url_ip, timeout=5)
                    if response.status_code == 200:
                        print(f"Connected via IP address")
                    else:
                        print(f"IP connection failed too")
                except:
                    print(f"IP connection failed too")
        
        print()


if __name__ == "__main__":
    import argparse
    
    # Argument parsing
    parser = argparse.ArgumentParser(description='Discover EweGo devices on the network')
    parser.add_argument('-t', '--timeout', type=int, default=10,
                       help='Discovery timeout in seconds (default: 10)')
    parser.add_argument('--test', action='store_true',
                       help='Test HTTP connection to discovered devices')
    args = parser.parse_args()
    
    # Discover devices
    devices = discover_devices(timeout=args.timeout)
    
    # Print summary
    print_summary(devices)
    
    # Optionally test connections
    if args.test and devices:
        print()
        test_device_connection(devices)
    
    print("\n" + "=" * 60)
    print("Discovery complete!")
    print("=" * 60)