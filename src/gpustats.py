# Copyright (c) 2026 tk-kh4i-dev. Licensed under the MIT License.

import ctypes
from ctypes import wintypes
import os
import platform
import subprocess

# local modules
from classes import GUID, DXGI_Adapter_Desc1, DXGI_QUERY_VMEM_INF
from debug_logger import r_logger # debug framework

# define how to get gpu info
def gpu_info():
    """Defines how to get the GPU name."""
    sys_name = platform.system()
    
    try:
        if sys_name == 'Windows':
            cmd = ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"]
            output = subprocess.check_output(cmd, universal_newlines=True, stderr=subprocess.DEVNULL)
            gpu_names = [line.strip() for line in output.splitlines() if line.strip()]
            return gpu_names if gpu_names else ["Unknown"]
        
        elif sys_name == 'Darwin':
            cmd = "system_profiler SPDisplaysDataType | grep 'Chipset Model'"
            output = subprocess.check_output(cmd, shell=True, universal_newlines=True, stderr=subprocess.DEVNULL)
            gpu_names = [line.split("Chipset Model:")[1].strip() for line in output.splitlines() if "Chipset Model:" in line]
            return gpu_names if gpu_names else ["Unknown"]
        
        elif sys_name == 'Linux':
            cmd = "lspci | grep -E 'VGA|3D'"
            output = subprocess.check_output(cmd, shell=True, universal_newlines=True, stderr=subprocess.DEVNULL)
            gpu_names = []
            for line in output.splitlines():
                if "controller:" in line:
                    gpu_names.append(line.split("controller:")[1].strip())
            return gpu_names if gpu_names else ["Unknown"]
    except Exception as e:
        r_logger.error("Failed to display GPU's info: %s", e)

    return ["Unknown"]

GPU_LIST = gpu_info() # global variable for easier implementation downstream

# virtual table
def call_vtable(obj, index, argtypes, *args):
    v_table = ctypes.cast(obj, ctypes.POINTER(ctypes.c_void_p))[0]
    func_ptr = ctypes.cast(v_table, ctypes.POINTER(ctypes.c_void_p))[index]
    proto = ctypes.WINFUNCTYPE(argtypes[0], ctypes.c_void_p, *argtypes[1:])
    return proto(func_ptr)(obj, *args)

def _dxgi_vram_usage():
    """Get VRAM usage using DXGI, Windows-only."""
    _gpu_vram_list = []

    try:
        dxgi = ctypes.windll.dxgi

        IID_IDXGIFactory1 = GUID("{770aae78-f26f-4dba-a829-253c83d1b387}")
        IID_IDXGIAdapter3 = GUID("{645967a4-1392-4310-a798-8053ce3e93fd}")

        factory = ctypes.c_void_p()
        if dxgi.CreateDXGIFactory1(ctypes.byref(IID_IDXGIFactory1), ctypes.byref(factory)) != 0:
            return _gpu_vram_list

        adapter_idx = 0
        while True:
            adapter1 = ctypes.c_void_p()
            hr = call_vtable(factory, 12, [wintypes.HRESULT, wintypes.UINT, ctypes.c_void_p], adapter_idx, ctypes.byref(adapter1))
            if hr != 0:
                break

            adapter3 = ctypes.c_void_p()
            hr_qi = call_vtable(adapter1, 0, [wintypes.HRESULT, ctypes.c_void_p, ctypes.c_void_p], ctypes.byref(IID_IDXGIAdapter3), ctypes.byref(adapter3))

            used_gb = 0.0
            total_gb = 0.0
            gpu_name = ""

            if hr_qi == 0:
                desc1 = DXGI_Adapter_Desc1()
                hr_desc1 = call_vtable(adapter1, 10, [wintypes.HRESULT, ctypes.c_void_p], ctypes.byref(desc1))

                memo_info_dedicated = DXGI_QUERY_VMEM_INF()
                memo_info_shared = DXGI_QUERY_VMEM_INF()

                used_mem = 0

                # dedicated video memory info
                hr_memo0 = call_vtable(adapter3, 14, [wintypes.HRESULT, wintypes.UINT, wintypes.UINT, ctypes.c_void_p], 0, 0, ctypes.byref(memo_info_dedicated))
                if hr_memo0 == 0:
                    used_mem = memo_info_dedicated.CurrentUsage

                # shared system video memory info (from system RAM)
                hr_memo1 = call_vtable(adapter3, 14, [wintypes.HRESULT, wintypes.UINT, wintypes.UINT, ctypes.c_void_p], 0, 1, ctypes.byref(memo_info_shared))
                if hr_memo1 == 0:
                    used_mem += memo_info_shared.CurrentUsage

                used_gb = used_mem / (1024**3)

                if hr_desc1 == 0 and desc1.VendorId != 0x1414:
                    gpu_name = desc1.Description
                    dedi_gb = desc1.DedicatedVideoMemory / (1024**3)
                    shar_gb = desc1.SharedSystemMemory / (1024**3)

                    # display dedicated vram info for a dGPU, for iGPU, 
                    # dedicated + shared because those usually have <1.5 GB of "dedicated" vram
                    total_gb = dedi_gb if dedi_gb >= 1.5 else (dedi_gb + shar_gb)
                
                call_vtable(adapter3, 2, [wintypes.ULONG])    
            call_vtable(adapter1, 2, [wintypes.ULONG])

            if gpu_name:
                _gpu_vram_list.append({"name": gpu_name, 
                                       "used": used_gb, 
                                       "total": total_gb, 
                                       "phys_id": adapter_idx})

            adapter_idx += 1
        call_vtable(factory, 2, [wintypes.ULONG])
    except Exception as e:
        r_logger.error("Failed to query VRAM usage info via dxgi: %s", e)

    return _gpu_vram_list

# get gpu stats such as loads and vram info
def get_gpu_stats():
    """Finds and returns GPU loads, vram usage."""
    infostat = []
    sys_name = platform.system()

    if sys_name == "Windows":
        try:
            import win32com.client
            wmi_obj = win32com.client.GetObject("winmgmts:\\\\.\\root\\cimv2")

            adapters = wmi_obj.ExecQuery("SELECT Name, AdapterRAM FROM Win32_VideoController")
            vram_totals = []
            for adapter in adapters:
                raw_ram = getattr(adapter, "AdapterRAM", 0) or 0

                try:
                    ram_b = int(raw_ram)
                    if ram_b < 0:
                        ram_b += 2**32
                except (ValueError, TypeError):
                    ram_b = 0

                vram_totals.append(ram_b / (1024 ** 3))

            perf_engine = []
            try:
                perf_engine = list(wmi_obj.ExecQuery("SELECT Name, UtilizationPercentage FROM Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine"))
            except Exception:
                pass

            vram_count = []
            try:
                vram_count = list(wmi_obj.ExecQuery("SELECT Name, DedicatedUsage FROM Win32_PerfFormattedData_GPUPerformanceCounters_GPUProcessMemory"))
            except Exception:
                pass

            vram_stats = _dxgi_vram_usage()

            for i in range(len(GPU_LIST)):
                # dxgi_idx = i # deprecated variable
                # phys_idx = len(GPU_LIST) - 1 - i
                
                gpu_name = GPU_LIST[i]

                match_dxgi = next(
                    (d for d in vram_stats if d.get("name") and (d["name"].lower() in gpu_name.lower() or gpu_name.lower() in d["name"].lower())),
                    None
                )
                
                phys_num = match_dxgi["phys_id"] if (match_dxgi and "phys_id" in match_dxgi) else i
                phys_key = f"phys_{phys_num}"
                
                active_loads = [
                    float(getattr(e, "UtilizationPercentage", 0) or 0) for e in perf_engine
                    if phys_key in str(getattr(e, "Name", ""))
                ]

                max_load = max(active_loads) if active_loads else 0

                # # This block of code is DEPRECATED. use alternative match_dxgi instead to fix vram/load index flips
                # fallback_Tvram = vram_totals[dxgi_idx] if dxgi_idx < len(vram_totals) else 0.0
                # if dxgi_idx < len(vram_stats) and isinstance(vram_stats[dxgi_idx], dict): # used to be a tuple here, changed to a dict
                #     _stats = vram_stats[dxgi_idx]
                #     used_vram = _stats.get("used", 0.0)
                #     total_vram = _stats.get("total", 0.0) or fallback_Tvram
                # else:
                #     used_vram = 0.0
                #     total_vram = vram_totals[dxgi_idx] if dxgi_idx < len(vram_totals) else 0.0
                
                # vram_b is kind of a placeholder name
                if match_dxgi:
                    used_vram = match_dxgi.get("used", 0.0)
                    total_vram = match_dxgi.get("total", 0.0)
                else:
                    vram_b = sum(
                        int(getattr(m, "DedicatedUsage", 0)) + int(getattr(m, "SharedUsage", 0)) for m in vram_count
                        if f"phys_{i}" in str(getattr(m, "Name", ""))
                    )

                    used_vram = vram_b / (1024**3)
                    total_vram = vram_totals[i] if i < len(vram_totals) else 0.0

                # gpu_name = GPU_LIST[i]
                # match_dxgi = next(
                #     (d for d in vram_stats if d.get("name") and (d["name"].lower() in gpu_name.lower() or gpu_name.lower() in d["name"].lower())),
                #     None
                # )

                # if match_dxgi and match_dxgi.get("total", 0) > 0:
                #     total_vram = match_dxgi["total"]
                # elif i < len(vram_totals):
                #     total_vram = vram_totals[i]
                # else:
                #     total_vram = 0.0

                infostat.append((max_load, used_vram, total_vram))
        except Exception as e:
            r_logger.error("Failed to retrieve GPU statistic info for Windows system: %s", e)

    elif sys_name == "Darwin":
        try:
            # macOS unified system memory stats
            total_vram_macos = 0.0

            try:
               total_mem_macos = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], stderr=subprocess.DEVNULL).strip()) # check vram capacity
               total_vram_macos = total_mem_macos / (1024**3)
            except Exception:
               pass

            gpu_load_macos = 0.0
            try:
                cmd = ["ioreg", "-r", "-d", "1", "-c", "IOAccelerator"]
                output = subprocess.check_output(cmd, encoding="utf-8", stderr=subprocess.DEVNULL)
                for line in output.splitlines():
                    if "Device Utilization %" in line:
                        gpu_load_macos = float(line.split("=")[-1].strip())
                        break
            except Exception:
                pass

            used_vram_macos = 0.0
            try:
                _vm_stat = subprocess.check_output(["vm_stat"], encoding="utf-8", stderr=subprocess.DEVNULL)
                _page = {}
                for line in _vm_stat.splitlines():
                    if ":" in line:
                        k, v = line.split(":")
                        _page[k.strip()] = int(v.strip().rstrip("."))

                page_size = 4096
                used_mem_macos = (_page.get("Pages active", 0) + _page.get("Pages wired down", 0)) * page_size
                used_vram_macos = used_mem_macos / (1024**3)
            except Exception:
                pass

            infostat.append((gpu_load_macos, used_vram_macos, total_vram_macos))
        except Exception as e:
            r_logger.error("Failed to retrieve GPU statistic info for MacOS: %s", e)

    elif sys_name == "Linux":
        try:
            # for NVIDIA GPUs
            import shutil

            _nvidia = False

            if shutil.which("nvidia-smi"):
                try:
                    cmd = [
                        "nvidia-smi",
                        "--query-gpu=utilization.gpu,memory.used,memory.total",
                        "--format=csv,noheader,nounits"
                    ]
                    output = subprocess.check_output(cmd, encoding="utf-8", stderr=subprocess.DEVNULL).strip()
                    for line in output.splitlines():
                        parts = [p.strip() for p in line.split(",")]
                        if len(parts) >= 3:
                            gpu_load_nvidia_linux = float(parts[0])
                            used_vram_nvidia_linux = float(parts[1]) / 1024.0
                            total_vram_nvidia_linux = float(parts[2]) / 1024.0

                    infostat.append((gpu_load_nvidia_linux, used_vram_nvidia_linux, total_vram_nvidia_linux))

                    _nvidia = True
                except Exception:
                    pass

            # for Intel/AMD GPUs
            if not _nvidia:
                drm_dir = "/sys/class/drm"

                if os.path.exists(drm_dir):
                    for card in sorted(os.listdir(drm_dir)):
                        if card.startswith("card") and "-" not in card:
                            device_dir = os.path.join(drm_dir, card, "device")

                            gpu_load_linux_file = os.path.join(device_dir, "gpu_busy_percent")
                            gpu_load_intelamd_linux = 0.0
                            if os.path.exists(gpu_load_linux_file):
                                try:
                                    with open(gpu_load_linux_file, "r") as f:
                                        gpu_load_intelamd_linux = float(f.read().strip())
                                except Exception:
                                    pass

                            total_vram_linux_file = os.path.join(device_dir, "mem_info_vram_total")
                            used_vram_linux_file = os.path.join(device_dir, "mem_info_vram_used")

                            used_vram_intelamd_linux = 0.0
                            total_vram_intelamd_linux = 0.0
                            if os.path.exists(total_vram_linux_file) and os.path.exists(used_vram_linux_file):
                                try:
                                    with open(total_vram_linux_file, "r") as f:
                                        total_vram_intelamd_linux = float(f.read().strip()) / (1024**3)
                                    with open(used_vram_linux_file, "r") as f:
                                        used_vram_intelamd_linux = float(f.read().strip()) / (1024**3)
                                except Exception:
                                    pass

            infostat.append((gpu_load_intelamd_linux, used_vram_intelamd_linux, total_vram_intelamd_linux))
        except Exception as e:
            r_logger.error("Failed to retrieve GPU statistic info for Linux system: %s", e)

    # when everything else failed, fallback to zeros for display so things don't break
    while len(infostat) < len(GPU_LIST):
        infostat.append((0, 0.0, 0.0))

    return infostat # fallback return