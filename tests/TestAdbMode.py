import unittest
from types import SimpleNamespace

from src.device_mode import (
    DeviceCaptureModeMixin,
    adb_status_device,
    capture_group,
    capture_method_for_device,
    startup_resolution_policy,
)


class FakeHandler:

    def __init__(self):
        self.posts = []

    def post(self, task, **kwargs):
        self.posts.append((task, kwargs))
        return True


class FakeDeviceManager:

    def __init__(self, app_config=None):
        self.windows_capture_config = {"capture_method": ["WGC", "BitBlt"]}
        self.device_dict = {
            "pc": {"imei": "pc", "device": "windows"},
            "phone": {"imei": "phone", "device": "adb", "emulator": None},
        }
        self.config = {"preferred": "pc", "capture": "BitBlt"}
        self.handler = FakeHandler()
        self.start_count = 0
        self.do_start_count = 0

    def get_devices(self):
        return list(self.device_dict.values())

    def get_preferred_device(self):
        return self.device_dict.get(self.config.get("preferred"))

    def set_capture(self, capture):
        self.config["capture"] = capture
        self.start()

    def set_preferred_device(self, imei=None, index=-1):
        if index != -1:
            imei = self.get_devices()[index]["imei"]
        if imei is not None:
            self.config["preferred"] = imei
        self.start()

    def start(self):
        self.start_count += 1

    def do_start(self):
        self.do_start_count += 1


class ModeAwareFakeDeviceManager(DeviceCaptureModeMixin, FakeDeviceManager):
    pass


class FakeAdbClient:

    def __init__(self, infos):
        self.infos = infos

    def list(self, extended=False):
        return self.infos

    @staticmethod
    def device(serial):
        return SimpleNamespace(serial=serial, prop=SimpleNamespace(model="Test Phone"))


class DiscoveryFakeDeviceManager(DeviceCaptureModeMixin):

    def __init__(self, infos):
        self.adb_capture_config = {}
        self._adb_client = FakeAdbClient(infos)
        self.device_dict = {
            "pc": {"imei": "pc", "device": "windows", "connected": True},
        }
        self.config = {"preferred": "pc", "capture": "WGC"}

    @property
    def adb(self):
        return self._adb_client

    def get_preferred_device(self):
        return self.device_dict.get(self.config.get("preferred"))

    @staticmethod
    def adb_get_imei(device):
        return f"android-{device.serial}"

    @staticmethod
    def get_resolution(device):
        return 1920, 1080


class TestAdbMode(unittest.TestCase):

    def test_physical_android_device_always_uses_adb_capture(self):
        device = {"device": "adb", "emulator": None}

        self.assertEqual("adb", capture_method_for_device(device, "WGC", ["WGC", "BitBlt"]))
        self.assertEqual("adb", capture_group(device))

    def test_android_emulator_keeps_ipc_capture_when_selected(self):
        device = {"device": "adb", "emulator": object()}

        self.assertEqual("ipc", capture_method_for_device(device, "ipc", ["WGC"]))
        self.assertEqual("adb-emulator", capture_group(device))

    def test_android_emulator_falls_back_to_adb_from_windows_capture(self):
        device = {"device": "adb", "emulator": object()}

        self.assertEqual("adb", capture_method_for_device(device, "WGC", ["WGC"]))

    def test_windows_device_restores_a_supported_capture(self):
        device = {"device": "windows"}

        self.assertEqual("BitBlt", capture_method_for_device(device, "BitBlt", ["WGC", "BitBlt"]))
        self.assertEqual("WGC", capture_method_for_device(device, "adb", ["WGC", "BitBlt"]))

    def test_physical_phone_skips_windows_resolution_gate(self):
        configured = {
            "ratio": "16:9",
            "min_size": (3840, 2160),
            "resize_to": [(1920, 1080)],
            "force_ratio": True,
        }

        policy = startup_resolution_policy(
            {"device": "adb", "emulator": None, "player_id": -1},
            configured,
        )

        self.assertIsNone(policy["ratio"])
        self.assertIsNone(policy["min_size"])
        self.assertFalse(policy["force_ratio"])
        self.assertEqual([(1920, 1080)], policy["resize_to"])
        self.assertEqual("16:9", configured["ratio"])

    def test_emulator_skips_windows_resolution_gate(self):
        configured = {
            "ratio": "16:9",
            "min_size": (3840, 2160),
            "force_ratio": True,
        }

        policy = startup_resolution_policy(
            {"device": "adb", "emulator": object()},
            configured,
        )

        self.assertIsNone(policy["ratio"])
        self.assertIsNone(policy["min_size"])
        self.assertFalse(policy["force_ratio"])
        self.assertEqual("16:9", configured["ratio"])

    def test_browser_device_uses_browser_capture(self):
        device = {"device": "browser"}

        self.assertEqual("browser", capture_method_for_device(device, "adb", ["WGC"]))

    def test_device_manager_switches_to_adb_and_restores_windows_capture(self):
        configured = {
            "ratio": "16:9",
            "min_size": (3840, 2160),
            "force_ratio": True,
        }
        app_config = {"supported_resolution": dict(configured)}
        manager = ModeAwareFakeDeviceManager(app_config)

        manager.set_preferred_device(index=1)
        self.assertEqual("phone", manager.config["preferred"])
        self.assertEqual("adb", manager.config["capture"])
        self.assertIsNone(app_config["supported_resolution"]["ratio"])
        self.assertIsNone(app_config["supported_resolution"]["min_size"])

        manager.set_preferred_device(index=0)
        self.assertEqual("pc", manager.config["preferred"])
        self.assertEqual("BitBlt", manager.config["capture"])
        self.assertEqual(configured, app_config["supported_resolution"])

    def test_saved_emulator_selection_applies_adb_policy_on_start(self):
        configured = {
            "ratio": "16:9",
            "min_size": (3840, 2160),
            "force_ratio": True,
        }
        app_config = {"supported_resolution": dict(configured)}
        manager = ModeAwareFakeDeviceManager(app_config)
        manager.device_dict["emulator"] = {
            "imei": "emulator",
            "device": "adb",
            "emulator": object(),
        }
        manager.config["preferred"] = "emulator"

        manager.do_start()

        self.assertEqual(1, manager.do_start_count)
        self.assertIsNone(app_config["supported_resolution"]["ratio"])
        self.assertIsNone(app_config["supported_resolution"]["min_size"])
        self.assertFalse(app_config["supported_resolution"]["force_ratio"])

    def test_latest_device_start_is_queued_while_an_old_start_may_be_running(self):
        manager = ModeAwareFakeDeviceManager()

        manager.start()

        _task, options = manager.handler.posts[-1]
        self.assertTrue(options["remove_existing"])
        self.assertFalse(options["skip_if_running"])

    def test_missing_phone_has_visible_adb_setup_row(self):
        manager = DiscoveryFakeDeviceManager([])

        manager.refresh_phones()

        status = manager.device_dict["adb-status:setup"]
        self.assertFalse(status["connected"])
        self.assertTrue(status["_adb_status_only"])
        self.assertIn("未检测到 ADB 手机", status["nick"])

    def test_unauthorized_phone_is_visible_with_instructions(self):
        info = SimpleNamespace(serial="phone-1", state="unauthorized", tags={})
        manager = DiscoveryFakeDeviceManager([info])

        manager.refresh_phones()

        status = manager.device_dict["adb-status:phone-1"]
        self.assertEqual("unauthorized", status["adb_state"])
        self.assertFalse(status["connected"])
        self.assertIn("USB 调试未授权", status["nick"])

    def test_authorized_phone_is_visible_as_connected(self):
        info = SimpleNamespace(serial="phone-1", state="device", tags={"model": "Pixel"})
        manager = DiscoveryFakeDeviceManager([info])

        manager.refresh_phones()

        phone = manager.device_dict["android-phone-1"]
        self.assertTrue(phone["connected"])
        self.assertEqual("Pixel", phone["nick"])
        self.assertEqual("1920x1080", phone["resolution"])

    def test_status_row_cannot_be_selected_as_a_working_device(self):
        manager = ModeAwareFakeDeviceManager()
        status = adb_status_device("phone-1", "unauthorized")
        manager.device_dict[status["imei"]] = status

        manager.set_preferred_device(imei=status["imei"])

        self.assertEqual("pc", manager.config["preferred"])


if __name__ == "__main__":
    unittest.main()
