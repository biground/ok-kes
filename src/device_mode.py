from collections.abc import Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from ok.gui.Communicate import communicate
from ok.util.logger import Logger


ADB_CAPTURE = "adb"
BROWSER_CAPTURE = "browser"
IPC_CAPTURE = "ipc"
WINDOWS_CAPTURE = "windows"

ADB_STATUS_PREFIX = "adb-status:"
logger = Logger.get_logger(__name__)


def adb_status_device(
    serial: str = "",
    state: str = "missing",
    model: str | None = None,
) -> dict[str, Any]:
    """Build a visible, non-selectable row for an unavailable ADB phone."""
    messages = {
        "missing": "未检测到 ADB 手机（连接 USB、开启 USB 调试后刷新）",
        "unauthorized": "USB 调试未授权（解锁手机并点“允许”）",
        "offline": "ADB 设备离线（重新插拔 USB 后刷新）",
        "error": "ADB 连接异常（检查手机驱动后刷新）",
    }
    message = messages.get(state, f"ADB 状态异常：{state}")
    nick = f"{model} — {message}" if model else message
    key = f"{ADB_STATUS_PREFIX}{serial or 'setup'}"
    return {
        "address": serial,
        "device": "adb",
        "connected": False,
        "imei": key,
        "nick": nick,
        "player_id": -1,
        "resolution": "",
        "adb_state": state,
        "_adb_status_only": True,
        "_physical_adb": True,
    }


def is_physical_adb_device(device: Mapping[str, Any] | None) -> bool:
    """Return whether a row represents a physical Android device."""
    return bool(
        device
        and device.get("device") == "adb"
        and device.get("emulator") is None
        and (device.get("_physical_adb") or device.get("player_id") == -1)
    )


def startup_resolution_policy(
    device: Mapping[str, Any] | None,
    configured_policy: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Disable the Windows-only startup resolution gate for ADB devices."""
    policy = dict(configured_policy or {})
    if device and device.get("device") == "adb":
        policy["ratio"] = None
        policy["min_size"] = None
        policy["force_ratio"] = False
    return policy


def capture_group(device: Mapping[str, Any] | None) -> str | None:
    """Return the capture preference group for a discovered device."""
    if not device:
        return None

    device_type = device.get("device")
    if device_type == "adb" and device.get("emulator") is not None:
        return "adb-emulator"
    return str(device_type) if device_type else None


def capture_method_for_device(
    device: Mapping[str, Any] | None,
    preferred_capture: str | None,
    windows_capture_methods: Iterable[str] = (),
) -> str | None:
    """Choose a capture backend that is valid for the selected device."""
    if not device:
        return preferred_capture

    device_type = device.get("device")
    if device_type == "adb":
        if device.get("emulator") is not None and preferred_capture in (ADB_CAPTURE, IPC_CAPTURE):
            return preferred_capture
        return ADB_CAPTURE

    if device_type == "browser":
        return BROWSER_CAPTURE

    if device_type == "windows":
        methods = list(windows_capture_methods)
        if preferred_capture in methods:
            return preferred_capture
        return methods[0] if methods else WINDOWS_CAPTURE

    return preferred_capture


class DeviceCaptureModeMixin:
    """Keep the active capture backend compatible with the selected device."""

    def __init__(self, *args, **kwargs):
        app_config = args[0] if args else kwargs.get("app_config")
        self._app_config = app_config if isinstance(app_config, dict) else None
        supported_resolution = (
            self._app_config.get("supported_resolution") if self._app_config else None
        )
        self._configured_supported_resolution = (
            dict(supported_resolution) if isinstance(supported_resolution, Mapping) else None
        )
        self._capture_by_device_group = {}
        super().__init__(*args, **kwargs)

    def set_capture(self, capture):
        device_group = capture_group(self.get_preferred_device())
        if device_group:
            self._capture_by_device_group[device_group] = capture
        return super().set_capture(capture)

    def start(self):
        """Queue the latest device state even if an older start is running."""
        return self.handler.post(
            self.do_start,
            remove_existing=True,
            skip_if_running=False,
        )

    def do_start(self):
        """Apply the device policy even when a saved selection is restored."""
        self._apply_startup_resolution_policy(self.get_preferred_device())
        return super().do_start()

    def refresh_phones(self, current=False):
        """Show every ADB state instead of hiding unauthorized/offline phones."""
        if self.adb_capture_config is None:
            return

        preferred = self.get_preferred_device()
        emulator_addresses = {
            device.get("address")
            for device in self.device_dict.values()
            if device.get("emulator") is not None
        }

        try:
            adb_infos = list(self.adb.list(extended=True))
            list_error = None
        except Exception as error:
            logger.error("Failed to list ADB devices", error)
            adb_infos = []
            list_error = error

        if current and preferred is not None:
            adb_infos = [
                info
                for info in adb_infos
                if info.serial == preferred.get("address")
            ]

        def refresh_one(info):
            if info.serial in emulator_addresses:
                return None

            model = getattr(info, "tags", {}).get("model")
            if info.state != "device":
                device = adb_status_device(info.serial, info.state, model)
                return device["imei"], device

            adb_device = self.adb.device(serial=info.serial)
            imei = self.adb_get_imei(adb_device)
            if not imei:
                device = adb_status_device(info.serial, "error", model)
                return device["imei"], device

            if any(
                device.get("emulator") is not None
                and device.get("adb_imei") == imei
                for device in self.device_dict.values()
            ):
                return None

            width, height = self.get_resolution(adb_device)
            if not model:
                try:
                    model = adb_device.prop.model
                except Exception:
                    model = None
            phone_device = {
                "address": info.serial,
                "device": "adb",
                "connected": True,
                "imei": imei,
                "nick": model or imei,
                "player_id": -1,
                "resolution": f"{width}x{height}",
                "adb_imei": imei,
                "adb_state": "device",
                "_physical_adb": True,
            }
            return imei, phone_device

        with ThreadPoolExecutor(max_workers=min(len(adb_infos), 8) if adb_infos else 1) as executor:
            results = [result for result in executor.map(refresh_one, adb_infos) if result]

        if not results and not current:
            state = "error" if list_error else "missing"
            status_device = adb_status_device(state=state)
            results = [(status_device["imei"], status_device)]

        new_keys = {key for key, _device in results}
        refreshed_addresses = {
            device.get("address") for _key, device in results if device.get("address")
        }
        for key, device in list(self.device_dict.items()):
            if not self._is_physical_adb(device) or key in new_keys:
                continue
            if not current or device.get("address") in refreshed_addresses:
                self.device_dict.pop(key, None)

        for key, device in results:
            self.device_dict[key] = device

        logger.debug(f"refresh_phones visible devices: {results}")

    def set_preferred_device(self, imei=None, index=-1):
        requested_device = self._requested_device(imei, index)
        if requested_device and requested_device.get("_adb_status_only"):
            logger.warning(f"ADB device is not ready: {requested_device}")
            communicate.adb_devices.emit(True)
            return None
        if requested_device is None and self.device_dict and all(
            device.get("_adb_status_only") for device in self.device_dict.values()
        ):
            communicate.adb_devices.emit(True)
            return None

        self._remember_capture(self.get_preferred_device())
        self._apply_startup_resolution_policy(requested_device)
        capture_changed = self._prepare_capture(requested_device)

        result = super().set_preferred_device(imei=imei, index=index)

        selected_device = self.get_preferred_device()
        self._apply_startup_resolution_policy(selected_device)
        if selected_device is not requested_device:
            capture_changed = self._prepare_capture(selected_device) or capture_changed
        if capture_changed:
            self.start()
        return result

    def _requested_device(self, imei, index):
        if index != -1:
            return self.get_devices()[index]
        selected_imei = self.config.get("preferred") if imei is None else imei
        return self.device_dict.get(selected_imei)

    @staticmethod
    def _is_physical_adb(device):
        return is_physical_adb_device(device)

    def _apply_startup_resolution_policy(self, device):
        if self._app_config is None or self._configured_supported_resolution is None:
            return

        current_policy = self._app_config.get("supported_resolution")
        if not isinstance(current_policy, dict):
            current_policy = {}
            self._app_config["supported_resolution"] = current_policy
        target_policy = startup_resolution_policy(
            device,
            self._configured_supported_resolution,
        )
        current_policy.clear()
        current_policy.update(target_policy)
        logger.info(
            f"startup resolution policy for {capture_group(device)}: {target_policy}"
        )

    def _remember_capture(self, device):
        device_group = capture_group(device)
        current_capture = self.config.get("capture")
        if device_group and current_capture:
            self._capture_by_device_group[device_group] = current_capture

    def _prepare_capture(self, device):
        if not device:
            return False

        device_group = capture_group(device)
        preferred_capture = self._capture_by_device_group.get(
            device_group,
            self.config.get("capture"),
        )
        windows_capture_methods = []
        if self.windows_capture_config:
            windows_capture_methods = self.windows_capture_config.get("capture_method", [])
        capture = capture_method_for_device(
            device,
            preferred_capture,
            windows_capture_methods,
        )
        if capture == self.config.get("capture"):
            return False

        self.config["capture"] = capture
        return True
