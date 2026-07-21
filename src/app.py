import ok
from ok import og
from ok.device.DeviceManager import DeviceManager as OkDeviceManager

from src.device_mode import DeviceCaptureModeMixin


class DeviceManager(DeviceCaptureModeMixin, OkDeviceManager):
    """ok-script device manager with reliable cross-device capture switching."""


class KesApp(ok.OK):
    """ok-kes application with device-aware Windows and ADB capture."""

    def __init__(self, config):
        self.device_manager = None
        super().__init__(config)

    def init_device_manager(self):
        if self.device_manager is None:
            self.device_manager = DeviceManager(
                self.config,
                self.exit_event,
                self.global_config,
            )
            og.device_manager = self.device_manager
