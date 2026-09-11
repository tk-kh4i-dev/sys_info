# Copyright (c) 2026 tk-kh4i-dev. Licensed under the MIT License.

import ctypes
from ctypes import wintypes
import uuid

# get vram info helper classes - for windows-only
class GUID(ctypes.Structure):
    """Defines how to get a GPU's GUID."""
    _fields_ = [
        ("_Data1", wintypes.DWORD),
        ("_Data2", wintypes.WORD),
        ("_Data3", wintypes.WORD),
        ("_Data4", wintypes.BYTE * 8)
    ]

    def __init__(self, guid_str):
        super().__init__()
        u = uuid.UUID(guid_str)

        self._Data1 = u.time_low
        self._Data2 = u.time_mid
        self._Data3 = u.time_hi_version
        self._Data4 = (wintypes.BYTE * 8).from_buffer_copy(u.bytes[8:])

class DXGI_Adapter_Desc1(ctypes.Structure):
    """Get the description of the GPU adapter using DXGI."""
    _fields_ = [
        ("Description", wintypes.WCHAR * 128), 
        ("VendorId", wintypes.UINT), 
        ("DeviceId", wintypes.UINT),
        ("SubSysId", wintypes.UINT), 
        ("Revision", wintypes.UINT), 
        ("DedicatedVideoMemory", ctypes.c_size_t),
        ("DedicatedSystemMemory", ctypes.c_size_t), 
        ("SharedSystemMemory", ctypes.c_size_t),
        ("AdapterLuid", GUID), 
        ("Flags", wintypes.UINT)
    ]

class DXGI_QUERY_VMEM_INF(ctypes.Structure):
    """Query memory (VRAM) info."""
    _fields_ = [
        ("Budget", ctypes.c_uint64),
        ("CurrentUsage", ctypes.c_uint64),
        ("AvailableForReservation", ctypes.c_uint64),
        ("CurrentReservation", ctypes.c_uint64)
    ]