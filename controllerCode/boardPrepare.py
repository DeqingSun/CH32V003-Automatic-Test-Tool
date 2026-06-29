"""CH334 USB hub discovery and per-port device listing.

Dependencies:
  brew install libusb          # macOS
  pip install -r controllerCode/requirements.txt
"""

import sys
import subprocess
import usb.core
import usb.util
from usb.core import USBError

minichlink_path = "/Users/deqinguser/Documents/GitHub/ch32fun/minichlink/minichlink"
ch32v305_controller_firmware_path = "/Users/deqinguser/Documents/GitHub/CH32V003-Automatic-Test-Tool/controllerCode/ch32v305_controller/build/ch32v305_controller_20260629.bin"
wch_linke_firmware_path = "/Users/deqinguser/Documents/GitHub/CH32V003-Automatic-Test-Tool/controllerCode/reference/WCH-LinkE-APP-IAP.bin"

HUB_VID = 0x1A86
HUB_PID = 0x8091
HUB_PORT_COUNT = 4

MACOS_LIBUSB_PATHS = (
    "/opt/homebrew/lib/libusb-1.0.dylib",
    "/usr/local/lib/libusb-1.0.dylib",
)

def _get_usb_backend():
    import usb.backend.libusb1

    backend = usb.backend.libusb1.get_backend()
    if backend is not None:
        return backend

    for path in MACOS_LIBUSB_PATHS:
        backend = usb.backend.libusb1.get_backend(find_library=lambda _name, lib_path=path: lib_path)
        if backend is not None:
            return backend
    return None


def find_ch334_hubs():
    """Return all connected WCH CH334/CH335 hubs (1a86:8091)."""
    return list(usb.core.find(find_all=True, idVendor=HUB_VID, idProduct=HUB_PID))


def _port_on_hub(device, hub):
    """Return the CH334 port number for device, or None if not downstream of hub."""
    current = device
    while current is not None:
        parent = current.parent
        if parent == hub:
            return current.port_number
        current = parent
    return None

def describe_device(dev):
    """Return device identity dict, tolerating unreadable string descriptors."""
    info = {
        "vid": dev.idVendor,
        "pid": dev.idProduct,
        "bus": dev.bus,
        "address": dev.address,
        "manufacturer": None,
        "product": None,
        "serial": None,
    }

    for field, index_attr in (
        ("manufacturer", "iManufacturer"),
        ("product", "iProduct"),
        ("serial", "iSerialNumber"),
    ):
        index = getattr(dev, index_attr, 0)
        if not index:
            continue
        try:
            info[field] = usb.util.get_string(dev, index)
        except USBError:
            pass

    return info


def devices_on_hub_ports(hub):
    """Map hub ports 1..4 to devices found by walking the USB parent chain."""
    ports = {port: [] for port in range(1, HUB_PORT_COUNT + 1)}

    for dev in usb.core.find(find_all=True):
        if dev == hub:
            continue
        port = _port_on_hub(dev, hub)
        if port is None or port < 1 or port > HUB_PORT_COUNT:
            continue
        ports[port].append(describe_device(dev))

    return ports



def main():
    backend = _get_usb_backend()
    if backend is None:
        print("libusb backend not found. Install libusb (e.g. brew install libusb).", file=sys.stderr)
        sys.exit(1)

    hubs = find_ch334_hubs()
    if not hubs:
        print(f"WCH CH334 hub not found ({HUB_VID:04x}:{HUB_PID:04x})", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(hubs)} WCH CH334 hubs")

    if len(hubs) > 1:
        print("More than one WCH CH334 hub found. This script only supports one hub for simplicity.")
        sys.exit(1)

    hub = hubs[0]

    
    devices = devices_on_hub_ports(hub)
    #check if port3 has 1209:c550
    ch32v305_controller_device_already_present = False
    if len(devices[3]) == 1:
        device = devices[3][0]
        if device["vid"] == 0x1209 and device["pid"] == 0xc550:
            ch32v305_controller_device_already_present = True
    if ch32v305_controller_device_already_present:
        print("CH32V305 controller device already present on port 3.")
    else:
        print("CH32V305 controller device not found on port 3.")
        print("Expect off board WCH-LinkE connected to pin header next to CH32V305CCT6.")
        #run minichlink -C linke -i to check if WCH-LinkE is connected, capture the output
        output = subprocess.check_output(
            [minichlink_path, "-C", "linke", "-i"],
            stderr=subprocess.STDOUT,
        ).decode("utf-8")
        #check if output contains "Detected CH32V305" and "Flash Storage: 288 kB"
        if not "Detected CH32V305" in output or not "Flash Storage: 288 kB" in output:
            print("WCH-LinkE not detected. Please connect WCH-LinkE to pin header next to CH32V305CCT6.")
            sys.exit(1)
        #check if the USER/RDPR has 20df/5aa5, the USER/RDPR and 20df/5aa5 must be in the same line
        value_of_USER_RDPR = output.split("USER/RDPR  : ")[1].split("\n")[0]
        if value_of_USER_RDPR == "20df/5aa5":
            print("WCH-LinkE is already configured for CH32V305 controller for memory split.")
        else:
            print("WCH-LinkE is not configured for CH32V305 controller for memory split.")
            #use minichlink -C linke -S 128 192 to configure WCH-LinkE for CH32V305 controller for memory split
            subprocess.check_output(
                [minichlink_path, "-C", "linke", "-S", "128", "192"],
                stderr=subprocess.STDOUT,
            ).decode("utf-8")
            print("WCH-LinkE is configured for CH32V305 controller for memory split.")
        #flash ch32v305_controller_firmware_path to port 3
        subprocess.check_output(
            [minichlink_path, "-C", "linke", "-w", ch32v305_controller_firmware_path, "0x08000000", "-b"],
            stderr=subprocess.STDOUT,
        ).decode("utf-8")
        print("CH32V305 controller firmware flashed to port 3.")
    #check if port4 has 1a86:8010
    wch_linke_device_already_present = False
    if len(devices[4]) == 1:
        device = devices[4][0]
        if device["vid"] == 0x1a86 and device["pid"] == 0x8010:
            wch_linke_device_already_present = True
    if wch_linke_device_already_present:
        print("WCH LinkE device already present on port 4.")
    else:
        #flash
        pass







if __name__ == "__main__":
    main()
