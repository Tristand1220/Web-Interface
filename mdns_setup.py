"""
MDNS for EweGo
Uses local netwrok to identify devices
"""

import socket 
from zeroconf import ServiceInfo, Zeroconf
import time

class EweGoMDNS:
    
    def __init__(self, device_id=None, port=5000):
        
        # Initialize mDNS reqs
        self.zeroconf = None
        self.service_info = None
        self.port = port
        
        # Get device identifier
        if device_id is None:
            self.device_id = socket.gethostname()
        else:
            self.device_id = device_id
            
        # Service type for local raspberry devices
        self.service_type = "_ewego._tcp.local."
        
        # Service name which will be unique to each device
        self.service_name = f"{self.device_id}.{self.service_type}"
        
    def start(self):
        
        # Starts advertsising to network
        try:
            # Create zeroconf instance
            self.zeroconf = Zeroconf()
            
            # Local Ip Address
            local_ip = self._get_local_ip()
            
            # Creating service information
            self.service_info = ServiceInfo(
                self.service_type,
                self.service_name,
                addresses=[socket.inet_aton(local_ip)],
                port=self.port,
                properties={
                    'device_id': self.device_id,
                    'service': 'EweGo System Health',
                    'version': '1.0',
                    'path': '/',
                    'api': '/api/health'
                },
                server=f"{self.device_id}.local."
            )
            
            # Registering service
            self.zeroconf.register_service(self.service_info)
            
            # print traceback
            print(f" mDNS service registered")
            print(f" Service Name: {self.service_name}")
            print(f" Device Id: {self.device_id}")
            print(f" Address: http://{self.device_id}.local:{self.port}")
            print(f" IP: HTTP://{local_ip}:{self.port}")
            
            return True
        
        except Exception as e:
            print(f" Failed to start mDNS service: {e}")
            return False
        
    def stop(self):
        # Stop mDNS service
        try:
            if self.zeroconf and self.service_info:
                self.zeroconf.unregister_service(self.service_info)
                self.zeroconf.close()
                print(" mDNS has stopped")
        except Exception as e:
            print(f" Error ending mDNS: {e}")
    
    def _get_local_ip(self):
        # Get local IP address
        
        try:
            # Creating a temporary socket to determine IP 
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80)) # connect to public DNS
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return "127.0.0.1" # Fallback to local host
        
if __name__ == "__main__":
    
    #Create mDNS instance
    mdns = EweGoMDNS(device_id="americanPI", port=5000)
    
    if mdns.start():
        print(" Service is now discoverable")
        print()
        print(f"   http://americanPI.local:5000")
        print()
        print(" Press Ctrl+C to stop")
        
        try:
            time.sleep(60*60) # Run for 1 hour (Testing purposes)
        except KeyboardInterrupt:
            print("\n\n Stopped by user")
        finally:
            mdns.stop()
    else:
        print(" Failed to start mDNS service")
    
        
    
        