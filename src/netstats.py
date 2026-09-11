# Copyright (c) 2026 tk-kh4i-dev. Licensed under the MIT License.

import platform
import re
import socket
import subprocess
import urllib.request

# local modules
from debug_logger import r_logger # debug framework

USE_BITS_NET_SPEED = True # option to either measure and display network speed in bytes or bits per second

def ping():
    """Send a ping to a server to get the latency value."""
    system = platform.system()

    # You can choose your own DNS server by replacing "8.8.8.8", 
    # but Google/Cloudflare or other large providers are recommended 
    # for better stability and data/signal integrity.

    target_host = "8.8.8.8" # dns server ip

    ipv6 = ":" in target_host

    # Applies if the system use IPV6 instead of IPV4.
    if system == 'Windows':
        ipv6_cmd = ["ping", "-6"] if ipv6 else ["ping"]
        cmd = ipv6_cmd + ["-n", "1", "-w", "1000", target_host]
    elif system == 'Darwin':
        ipv6_mac = "ping6" if ipv6 else "ping"
        cmd = [ipv6_mac, "-c", "1", "-W", "1000", target_host]
    elif system == 'Linux':
        ipv6_linux = "ping6" if ipv6 else "ping"
        cmd = [ipv6_linux, "-c", "1", "-W", "1", target_host]
    else:
        return "Disconnected"
    
    try:
        output = subprocess.run(
            cmd, 
            universal_newlines=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        result = output.stdout.lower()
        
        match = re.search(r"(?:time[=<]\s*)?(\d+(?:\.\d+)?)\s*ms", result)
        
        if match:
            return f"{match.group(1)} ms"

        # if packet loss is 100% even with 3 ping tries then fallback to offline state
        if "timed out" in result or "100% packet loss" in result or "unreachable" in result:
            return "Disconnected"
    except Exception as e:
        r_logger.warning("Failed to process ping latency: %s", e)
        return "Disconnected"

def pvt_ip():
    """Finds the private ip of the system it is executed on."""
    try:
        # find the local system's private ip by open a socket on port 80
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # obviously you can swap 8.8.8.8 for your DNS server of choice that's able to return your IP, 
            # but 8.8.8.8 is default here
            target_host = "8.8.8.8"
            s.connect((target_host, 80))
            return s.getsockname()[0]
    except Exception as e:
        r_logger.warning("Failed to resolve IP (private): %s", e)
        return "127.0.0.1 (Offline)"

def pub_ip():
    """Finds the public ip of the system it is executed on."""
    # if opening a socket to google via port 80 in pvt_ip failed then there is a network issue,
    # then fallback to offline state
    if pvt_ip() == "127.0.0.1 (Offline)":
        return "127.0.0.1 (Offline)"
    
    try:
        with urllib.request.urlopen('https://api.ipify.org', timeout=5) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        r_logger.warning("Failed to resolve public IP: %s", e)
        return "Unknown (Web API Error)"
        
def net_speed(b_delta):
    """Format the internet speed measurement logic."""
    if USE_BITS_NET_SPEED: # bits per second logic
        speed = float(b_delta) * 8
        units = ['bps', 'Kbps', 'Mbps', 'Gbps', 'Tbps', 'Pbps', 'Ebps']
    else: # bytes per second logic
        speed = float(b_delta)
        units = ['B/s', 'KB/s', 'MB/s', 'GB/s', 'TB/s', 'PB/s', 'EB/s']
        
    factor = 1000.0 # factor is 1000.0 by default

    for u in units:
        if speed < factor or u == units[-1]:
            break
        speed /= factor
    return f"{speed:.1f} {u}"