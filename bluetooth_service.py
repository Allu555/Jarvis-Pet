"""
Bluetooth Service for Origin Island
Monitors connected Bluetooth accessories (headphones, earbuds, speakers, controllers)
and provides real-time device names and connection status.
"""

import subprocess
import threading
import time
from typing import List, Callable, Optional


class BluetoothInfo:
    def __init__(self, connected_devices: Optional[List[str]] = None, is_enabled: bool = True):
        self.connected_devices: List[str] = connected_devices or []
        self.is_enabled: bool = is_enabled

    @property
    def has_connected(self) -> bool:
        return len(self.connected_devices) > 0

    @property
    def primary_device_name(self) -> str:
        if self.connected_devices:
            return self.connected_devices[0]
        return "No Bluetooth Connected"

    def __repr__(self) -> str:
        return f"<BluetoothInfo connected={self.connected_devices} enabled={self.is_enabled}>"


class BluetoothService:
    _instance: Optional['BluetoothService'] = None

    @classmethod
    def get_instance(cls) -> 'BluetoothService':
        if cls._instance is None:
            cls._instance = BluetoothService()
        return cls._instance

    def __init__(self):
        self._current_info = BluetoothInfo()
        self._lock = threading.Lock()
        self._listeners: List[Callable[[BluetoothInfo], None]] = []
        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="BluetoothServiceWorker")
        self._thread.start()

    def add_listener(self, callback: Callable[[BluetoothInfo], None]):
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)
                callback(self._current_info)

    @property
    def current_info(self) -> BluetoothInfo:
        with self._lock:
            return self._current_info

    def _notify_listeners(self, info: BluetoothInfo):
        for cb in list(self._listeners):
            try:
                cb(info)
            except Exception:
                pass

    def _query_connected_devices(self) -> BluetoothInfo:
        devices: List[str] = []
        is_enabled = True

        # Pure in-process Windows Runtime BluetoothDevice API via winsdk (Zero process spawns)
        try:
            import asyncio
            import winsdk.windows.devices.enumeration as de
            import winsdk.windows.devices.bluetooth as bt

            async def _check_winsdk():
                connected = []
                devs = await de.DeviceInformation.find_all_async()
                for d in devs:
                    if "BTHENUM#DEV_" in d.id.upper():
                        try:
                            b = await bt.BluetoothDevice.from_id_async(d.id)
                            if b and b.connection_status == bt.BluetoothConnectionStatus.CONNECTED:
                                name = b.name.strip()
                                if name and name not in connected:
                                    connected.append(name)
                        except Exception:
                            pass
                return connected

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                winsdk_devices = loop.run_until_complete(_check_winsdk())
                loop.close()
                if winsdk_devices:
                    devices.extend(winsdk_devices)
            except Exception:
                pass
        except Exception:
            pass

        return BluetoothInfo(connected_devices=devices, is_enabled=is_enabled)

    def _worker_loop(self):
        while self._running:
            try:
                info = self._query_connected_devices()
                changed = False
                with self._lock:
                    if self._current_info.connected_devices != info.connected_devices or self._current_info.is_enabled != info.is_enabled:
                        self._current_info = info
                        changed = True

                if changed:
                    self._notify_listeners(info)
            except Exception:
                pass

            # Low power: Poll accessories gently every 10 seconds instead of hammering the CPU every 3s
            time.sleep(10.0)
