# Copyright (c) 2026 tk-kh4i-dev. Licensed under the MIT License.

import platform

# local modules
from debug_logger import r_logger # debug framework

# find and return os information
def os_inf():
    """Finds and display OS information such as OS name, build number, architecture, etc..."""
    system = platform.system()

    if system == "Windows":
        try:
            import winreg

            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
        
            product_name, _ = winreg.QueryValueEx(key, "ProductName")
            
            build_str, _ = winreg.QueryValueEx(key, "CurrentBuildNumber")
            build_clean = "".join(filter(str.isdigit, str(build_str))) # only accept the string if the string is all digits, which make up the build number, e.g. '26100'.
            build_num = int(build_clean) if build_clean else 0

            try:
                ubr_val, _ = winreg.QueryValueEx(key, "UBR")
                ubr_str = f".{ubr_val}"
            except FileNotFoundError:
                ubr_str = ""

            # display the service pack rev. on older Windows versions, 'sp' refers to 'service pack', 
            # sorry if it feels too abbreviated.
            sp_str = ""
            try:
                csd_val, _ = winreg.QueryValueEx(key, "CSDVersion")
                if csd_val:
                    sp_clean = "".join(filter(str.isdigit, str(csd_val))) # also only accept string if string is all digits.
                    if sp_clean:
                        sp_str = f" SP{sp_clean}"
            except FileNotFoundError:
                pass

            winreg.CloseKey(key)

            # Fix Windows 10 -> 11 label
            if build_num >= 22000 and "Windows 10" in product_name:
                product_name = product_name.replace("Windows 10", "Windows 11")
                
            return f"{product_name}{sp_str} (Build {build_str}{ubr_str} - {platform.machine()})"
        except Exception as e:
            r_logger.error("Failed to read registry values: %s", e)
            return f"Windows {platform.release()}"
    
    elif system == "Darwin":
        return f"macOS {platform.mac_ver()[0]}"
    
    elif system == "Linux":
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        parts = line.split("=", 1)
                        if len(parts) > 1:
                            return parts[1].strip().strip('"').strip("'")
        except Exception as e:
            r_logger.error("Failed to read /etc/os-release: %s", e)
            return f"Linux {platform.release()}"
    
    # in case anything else fail
    uname = platform.uname()
    return f"{uname.system} {uname.release}"