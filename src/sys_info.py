# Copyright (c) 2026 tk-kh4i-dev. Licensed under the MIT License.

"""
Copyright (c) 2026 tk-kh4i-dev. Licensed under the MIT License.

Can be used for displaying the current system's information

LICENSE: See details in 'LICENSE' in root directory
""" 

import multiprocessing
import os
import platform
import sys
import re
import time

import colorama
from colorama import Fore, Style
import cpuinfo
import psutil

# local modules
import debug_logger
from debug_logger import r_logger # debug framework
from gpustats import GPU_LIST, get_gpu_stats # retrieve system's GPU info such as name and resource usage
from netstats import pub_ip, pvt_ip, ping, net_speed # network stats worker
from os_info import os_inf # display system OS information

colorama.init(autoreset=True)

__version__ = "2.16.0" # utility version, all modules within src/ follow this version

UI_WIDTH = 70
BAR_LENGTH = 20

CPU_NAME = cpuinfo.get_cpu_info()['brand_raw']
PUB_IP = "Initializing ..."
net_start = psutil.net_io_counters()

BIN_AUTO = True
BIN_MANUAL = False

OS_BIN_DEFAULTS = {
    "Windows": True,
    "Darwin": False,
    "Linux": False,
}

ANSI_ESC = re.compile(r'\x1b\[[0-9;]*[mK]')

# left-align text and ignore non-printable ANSI escape sequences
def ljust_ansi_ignore(text, width, fillchar=' '):
    visi_len = len(ANSI_ESC.sub('', text))
    padding = max(0, width - visi_len)
    return text + (fillchar * padding)

def format_l(text=""):
    inn_width = UI_WIDTH - 2
    return f"│ {ljust_ansi_ignore(text, inn_width)} │"
    
def size(n_bytes):
    if BIN_AUTO:
        # finds current OS, if OS is Windows, factor = 1024, if OS is unknown, default to factor of 1000
        current_os = platform.system()
        use_binary = OS_BIN_DEFAULTS.get(current_os)
    else:
        use_binary = BIN_MANUAL

    factor = 1024 if use_binary else 1000

    for unit in ["", "K", "M", "G", "T", "P", "E", "Z", "Y"]: # data size units
        if n_bytes < factor:
            suffix = "B" if (unit == "" or not use_binary) else "iB"
            return f"{n_bytes:.2f} {unit}{suffix}"
        n_bytes /= factor

def draw_header(title, version):
    version_str = f"v{__version__}"
    header_text = f"{title} {version}"
    inn_width = UI_WIDTH - 2
    
    print("┌" + "─" * UI_WIDTH + "┐")
    print(f"│ {header_text.center(inn_width)} │")
    print(f"│ {version_str.center(inn_width)} │")
    print("├" + "─" * UI_WIDTH + "┤")

def draw_footer():
    print("└" + "─" * UI_WIDTH + "┘")

def display_specs():
    """This is the main loop (function) for the utility."""
    print("\033[H", end="", flush=True)

    # define the networking logic variables downstream beforehand
    global net_start

    net_now = psutil.net_io_counters()

    dload_delta = net_now.bytes_recv - net_start.bytes_recv
    uload_delta = net_now.bytes_sent - net_start.bytes_sent

    net_start = net_now
    
    dload_str = net_speed(dload_delta)
    uload_str = net_speed(uload_delta)

    draw_header("SYSTEM DIAGNOSTICS & MONITOR", "")
    
    # OS Info
    uname = platform.uname()
    full_os = os_inf()
    print(format_l(f"[SYS] OS: {full_os}"))
    print(format_l(f"[SYS] Hostname: {uname.node}"))
    
    # CPU Info
    print("├" + "─" * UI_WIDTH + "┤")
    max_cpu_len = UI_WIDTH - 16
    cpu_name = CPU_NAME[:max_cpu_len] if len(CPU_NAME) > max_cpu_len else CPU_NAME
    print(format_l(f"[CPU] Model: {cpu_name}"))

    cpufreq = psutil.cpu_freq()
    if cpufreq:
        print(format_l(f"[CPU] Base Clock: {cpufreq.max / 1000:.2f} GHz"))

    print(format_l(f"[CPU] Cores: {psutil.cpu_count(logical=False)} Physical | {psutil.cpu_count(logical=True)} Logical"))
    
    cpu_usage = psutil.cpu_percent(interval=0)
    if cpu_usage >= 80:
        cpu_bar_color = Fore.RED + Style.BRIGHT
    elif cpu_usage >= 60:
        cpu_bar_color = Fore.YELLOW + Style.BRIGHT
    else:
        cpu_bar_color = Fore.WHITE + Style.BRIGHT

    bar_length = BAR_LENGTH
    filled_length = int(round(bar_length * cpu_usage / 100))
    bar = cpu_bar_color + '█' * filled_length + Style.RESET_ALL + '░' * (bar_length - filled_length)
    print(format_l(f"[CPU] Load: [{bar}] {cpu_bar_color}{cpu_usage}%{Style.RESET_ALL}"))
    
    # Memory Info
    print("├" + "─" * UI_WIDTH + "┤")
    svmem = psutil.virtual_memory()
    print(format_l(f"[MEM] Total: {size(svmem.total)} | Available: {size(svmem.available)}"))

    if svmem.percent >= 80:
        ram_bar_color = Fore.RED + Style.BRIGHT
    elif svmem.percent >= 60:
        ram_bar_color = Fore.YELLOW + Style.BRIGHT
    else:
        ram_bar_color = Fore.WHITE + Style.BRIGHT

    ram_filled = int(round(bar_length * svmem.percent / 100))
    ram_bar = ram_bar_color + '█' * ram_filled + Style.RESET_ALL + '░' * (bar_length - ram_filled)
    print(format_l(f"[MEM] Usage: [{ram_bar}] {ram_bar_color}{svmem.percent}%{Style.RESET_ALL}"))

    # GPU Info
    print("├" + "─" * UI_WIDTH + "┤")
    gpu_stats = get_gpu_stats()

    for idx, gpu_name in enumerate(GPU_LIST):
        if idx < len(gpu_stats):
            cur_stat = gpu_stats[idx]

        while isinstance(cur_stat, (tuple, list)) and len(cur_stat) == 1 and isinstance(cur_stat[0], (tuple, list)):
            cur_stat = cur_stat[0]

        gpu_load_used, vram_used, vram_total = (list(cur_stat) + [0, 0.0, 0.0])[:3]
        gpu_load_total = 100
       
        # Extract the number if it's wrapped in a tuple/list, then convert to float
        if isinstance(gpu_load_used, (tuple, list)):
            gpu_load_used = float(gpu_load_used[0])
        else:
            float(gpu_load_used)

        if isinstance(vram_used, (tuple, list)):
            vram_used = float(vram_used[0]) 
        else: 
            float(vram_used)

        if isinstance(vram_total, (tuple, list)):
            vram_total = float(vram_total[0])
        else: 
            float(vram_total)
        
        if 0.0 < vram_total < 1.0:
            # Format in MB (convert GB to MB)
            vram_str = f"{vram_used * 1024:.0f} / {vram_total * 1024:.0f} MB"
        else:
            # Format in GB
            vram_str = f"{vram_used:.2f} / {vram_total:.2f} GB"

        stats = f"{gpu_load_used:.0f} / {gpu_load_total}% | {vram_str}"

        max_gpu_len = (UI_WIDTH - 2) - len(f"[GPU {idx}] ") - len(stats) - 1
        gpu_tchard = gpu_name[:max_gpu_len] if len(gpu_name) > max_gpu_len else gpu_name # tchard = truncated

        l_char = f"[GPU {idx}] {gpu_tchard}"
        space_gap = " " * max(1, (UI_WIDTH - 2) - len(l_char) - len(stats))

        print(format_l(f"{l_char}{space_gap}{stats}"))
    
    # Network Info
    print("├" + "─" * UI_WIDTH + "┤")
    ping_info = ping()
    public_ip = PUB_IP
    private_ip = pvt_ip()
    print(format_l(f"[NET] Public IP: {public_ip}"))
    print(format_l(f"[NET] Local IP: {private_ip}"))
    print(format_l(f"[NET] Download: {dload_str} | Upload: {uload_str}"))
    print(format_l(f"[NET] Latency: {ping_info}"))

    # Disk Info
    print("├" + "─" * UI_WIDTH + "┤")
    print(format_l("[DSK] Mountpoint         Total          Used          Usage"))
    
    for partition in psutil.disk_partitions():
        if 'loop' in partition.device or not partition.fstype:
            continue

        try:
            partition_usage = psutil.disk_usage(partition.mountpoint)
            
            if partition_usage.percent >= 90:
                disk_bar_color = Fore.RED + Style.BRIGHT
            elif partition_usage.percent >= 80:
                disk_bar_color = Fore.YELLOW + Style.BRIGHT
            else:
                disk_bar_color = Fore.WHITE + Style.BRIGHT

            p_str = f"      ├─ {partition.mountpoint:<12} " \
                    f"{size(partition_usage.total):<10} " \
                    f"    {size(partition_usage.used):<10} " \
                    f"      {disk_bar_color}{partition_usage.percent}%{Style.RESET_ALL}"
            
            print(format_l(p_str))
        except (PermissionError, OSError, ValueError) as e:
            r_logger.error("Couldn't display disk information for %s: %s", partition.mountpoint, e)
            continue

    draw_footer()

def main():
    global PUB_IP

    is_debug = "--debug" in sys.argv[1:]

    if is_debug:
        debug_logger.ini_log("DEBUG")
    else:
        debug_logger.ini_log()

    if os.name == 'nt':
        try:
            os.system('')
        except Exception:
            pass

    # for dramatic effects
    if is_debug:
        r_logger.info("[!] Starting ...")
        time.sleep(0.4)

        r_logger.info("Initializing system diagnostics ...")
        time.sleep(0.8)

        r_logger.info("Starting network monitor ...")
        time.sleep(0.8)

        r_logger.info("Startup completed.")
        time.sleep(0.3)
    else:
        print("[!] Starting ...", flush=True)
        time.sleep(0.4)

        print("Initializing system diagnostics ...", flush=True)
        time.sleep(0.8)

        print("Starting network monitor ...", flush=True)
        time.sleep(0.8)

        print("Startup completed.", flush=True)
        time.sleep(0.3)

    PUB_IP = pub_ip()
    print(f"Public IP: {PUB_IP}")

    try:
        print("\033[H\033[?25l", end="", flush=True)

        while True:
            display_specs() # the loop runs here in main
            time.sleep(1) # refresh the loop every 1 second
    except (KeyboardInterrupt, SystemExit) as e:
        # calculate exit code and give it to sys.exit, default value is 0
        code = getattr(e, "code", 0)
        exit_code = code if isinstance(code, int) else 0

        exit_msg = "\n\n[!] Stopping ..." # message that gets displayed when exiting
        
        if is_debug:
            r_logger.info(exit_msg)
            time.sleep(0.8)

            r_logger.info("Process terminated. Exit code: %s.", exit_code)
        else:
            print(exit_msg, flush=True)
            time.sleep(0.8)
    finally:
        print("\033[?25h", end="", flush=True)

    sys.exit(exit_code)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()