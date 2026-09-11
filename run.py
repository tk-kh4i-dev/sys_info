# Copyright (c) 2026 tk-kh4i-dev. Licensed under the MIT License.

"""
To use, execute 'python/python3 run.py' in a terminal.
"""

import os
import sys
import struct
import platform

# compatibility checks
def compa_check():
    if struct.calcsize("P") * 8 != 64:
        sys.exit("ERROR: This utility must be executed on a 64-bit Python installation")

    if sys.version_info < (3, 6):
        sys.exit("ERROR: This utility must be executed using at least Python 3.6")

    system = os.name
    system1 = sys.platform

    if system == 'nt':
        winver = sys.getwindowsversion()

        if winver.major < 6 or (winver.major == 6 and winver.minor < 1):
            sys.exit("ERROR: OSes older than Windows 7 SP1 or Windows Server 2008 R2 is not supported.")

        win64 = os.environ.get('PROCESSOR_ARCHITECTURE', '').endswith('64') or \
                os.environ.get('PROCESSOR_ARCHITEW6432') is not None
        
        if not win64:
            sys.exit("ERROR: This utility requires a 64-bit Windows operating system.")

        if winver.major < 10:
            sysroot = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'))
            ucrt = os.path.join(sysroot, 'ucrtbase.dll')

            if not os.path.exists(ucrt):
                sys.exit(
                    "ERROR: Universal C Runtime extension not found.\n"
                    "Please install update KB2999226 before continuing."
                )
    
    elif system1 == 'darwin':
        machine = platform.machine()
        mac64 = '64' in machine or machine == 'x86_64' or machine == 'arm64'
    
        if not mac64:
            sys.exit("ERROR: This utility requires a 64-bit macOS operating system.")
    
        try:
            macver = platform.mac_ver()[0]
            macparts = [int(x) for x in macver.split('.')[:2]]

            while len(macparts) < 2:
                macparts.append(0)

            if macparts[0] < 10 or (macparts[0] == 10 and macparts[1] < 9):
                sys.exit("ERROR: This utility requires macOS X 10.9 (Mavericks) or newer.")
        except (ValueError, IndexError):
            pass

    elif system1.startswith('linux'):
        machine = platform.machine()
        linux64 = '64' in machine or machine == 'amd64'

        if not linux64:
            sys.exit("ERROR: This utility can only execute on a 64-bit Linux distribution.")

        try:
            kernelver = platform.release().split('-')[0]
            kernelparts = [int(x) for x in kernelver.split('.')[:3]]

            while len(kernelparts) < 3:
                kernelparts.append(0)

            if tuple(kernelparts) < (2, 6, 13):
                sys.exit("ERROR: Execution needs Linux Kernel 2.6.13 or newer.")
        except (ValueError, IndexError):
            pass

compa_check()

import pathlib # if compa_check() succeeds, import pathlib 
    
# finds and maps the files/directories
src_dir = pathlib.Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from sys_info import main # import our function that does the loop from sys_info.py

# execute sys_info.py and handover control to it
if __name__ == "__main__":
    main()