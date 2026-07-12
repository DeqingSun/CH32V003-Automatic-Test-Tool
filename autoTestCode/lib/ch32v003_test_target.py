import os
import subprocess
import time

from .ch32V305CCT6_test_tool import Ch32V305CCT6_test_tool
from .minichlink_util import locate_minichlink


class Ch32V003_test_target:
    def __init__(self):
        self.test_tool = Ch32V305CCT6_test_tool()
        self.map_dict = {
            "PD4": self.test_tool.SSOP20_PIN1_MAP,
            "PD5": self.test_tool.SSOP20_PIN2_MAP,
            "PD6": self.test_tool.SSOP20_PIN3_MAP,
            "PD7": self.test_tool.SSOP20_PIN4_MAP,
            "PA1": self.test_tool.SSOP20_PIN5_MAP,
            "PA2": self.test_tool.SSOP20_PIN6_MAP,
            "VSS": self.test_tool.SSOP20_PIN7_MAP,
            "PD0": self.test_tool.SSOP20_PIN8_MAP,
            "VDD": self.test_tool.SSOP20_PIN9_MAP,
            "PC0": self.test_tool.SSOP20_PIN10_MAP,
            "PC1": self.test_tool.SSOP20_PIN11_MAP,
            "PC2": self.test_tool.SSOP20_PIN12_MAP,
            "PC3": self.test_tool.SSOP20_PIN13_MAP,
            "PC4": self.test_tool.SSOP20_PIN14_MAP,
            "PC5": self.test_tool.SSOP20_PIN15_MAP,
            "PC6": self.test_tool.SSOP20_PIN16_MAP,
            "PC7": self.test_tool.SSOP20_PIN17_MAP,
            "PD1": self.test_tool.SSOP20_PIN18_MAP,
            "PD2": self.test_tool.SSOP20_PIN19_MAP,
            "PD3": self.test_tool.SSOP20_PIN20_MAP,
            "X0": self.test_tool.PIN_X0,
            "X1": self.test_tool.PIN_X1,
            "X2": self.test_tool.PIN_X2,
            "X3": self.test_tool.PIN_X3,
            "X4": self.test_tool.PIN_X4,
            "X5": self.test_tool.PIN_X5,
            "X6": self.test_tool.PIN_X6,
            "WCH_LINKE_SWDIO": self.test_tool.WCH_LINKE_SWDIO,
            "WCH_LINKE_SWCLK": self.test_tool.WCH_LINKE_SWCLK,
            "WCH_LINKE_TX": self.test_tool.WCH_LINKE_TX,
            "WCH_LINKE_RX": self.test_tool.WCH_LINKE_RX,
            "WCH_LINKE_RST": self.test_tool.WCH_LINKE_RST,
            "305_PA0": self.test_tool.Y_305_PA0,
            "305_PA1": self.test_tool.Y_305_PA1,
            "305_PA2": self.test_tool.Y_305_PA2,
            "305_PA3": self.test_tool.Y_305_PA3,
            "305_PA4": self.test_tool.Y_305_PA4,
            "305_PA5": self.test_tool.Y_305_PA5,
            "305_PA6": self.test_tool.Y_305_PA6,
            "305_PA7": self.test_tool.Y_305_PA7,
        }

    def initialize(self):
        self.test_tool.connect()
        ret = self.test_tool.initailize(0.5)
        if (ret == True):
            return True
        else:
            return False

    def resetMatrix(self):
        ret = self.test_tool.initailize(0.5)
        if (ret == True):
            return True
        else:
            return False

    def connectPin(self, pin_name, pin_305_gpio_name):
        if (pin_name not in self.map_dict):
            print("Pin not found: "+pin_name)
            return False
        if (pin_305_gpio_name not in self.map_dict):
            print("Pin not found: "+pin_305_gpio_name)
            return False
        self.test_tool.connect_pins(self.map_dict[pin_name], self.map_dict[pin_305_gpio_name], 0.5)
        return True

    def locateMinichlink(self):
        return locate_minichlink()

    def _minichlink_linke_cmd(self, minichlink, wch_linke_serial_number=None, *extra):
        cmd = [minichlink, "-C", "linke"]
        if wch_linke_serial_number is not None:
            cmd.extend(["-l", str(wch_linke_serial_number)])
        cmd.extend(extra)
        return cmd

    def _detect_ch32v003(self, minichlink, wch_linke_serial_number=None):
        cmd = self._minichlink_linke_cmd(minichlink, wch_linke_serial_number)
        result = subprocess.run(cmd, capture_output=True, text=True)
        out = (result.stdout or "") + (result.stderr or "")
        return "Detected CH32V003" in out

    def _minichlink_detect_info(self, minichlink, wch_linke_serial_number=None):
        cmd = self._minichlink_linke_cmd(minichlink, wch_linke_serial_number)
        result = subprocess.run(cmd, capture_output=True, text=True)
        out = (result.stdout or "") + (result.stderr or "")
        return {
            "out": out,
            "detected": "Detected CH32V003" in out,
            "rdp_enabled": "Read protection: enabled" in out,
        }

    def _write_firmware_image(self, minichlink, firmware_path, wch_linke_serial_number=None,
                              halt=False):
        # halt=True: -a ... -b so the first attach after NRST release can program
        # before DisableSDI()/PD1 reuse runs again.
        extra = []
        if halt:
            extra.append("-a")
        extra.extend(["-w", firmware_path, "0x08000000"])
        if halt:
            extra.append("-b")
        cmd = self._minichlink_linke_cmd(minichlink, wch_linke_serial_number, *extra)
        result = subprocess.run(cmd, capture_output=True, text=True)
        out = (result.stdout or "") + (result.stderr or "")
        return "Image written" in out, out

    def _route_swio(self):
        tt = self.test_tool
        tt.connect_pins(tt.SSOP20_PIN18_MAP, tt.Y_305_PA7, 0.5)  # PD1 / SWIO
        tt.connect_pins(tt.WCH_LINKE_SWDIO, tt.Y_305_PA7, 0.5)

    def _option_bytes_write_protected(self, minichlink, wch_linke_serial_number=None):
        """True if RDPR/WRPR block programming (minichlink -i)."""
        cmd = self._minichlink_linke_cmd(minichlink, wch_linke_serial_number, "-i")
        result = subprocess.run(cmd, capture_output=True, text=True)
        out = (result.stdout or "") + (result.stderr or "")
        if "Read protection: enabled" in out:
            return True
        # WRPR0/1 displayed as nWRPR/WRPR halfwords; protected pages use WRPR=0x00
        # e.g. WRPR1/WRPR0: ff00/ff00  vs unlocked 00ff/00ff
        for line in out.splitlines():
            if "WRPR1/WRPR0" in line and "ff00" in line.replace(" ", "").lower():
                return True
        return False

    def _clear_flash_protection(self, minichlink, wch_linke_serial_number=None):
        """Clear RDPR/WRPR, then power-cycle so option bytes reload.

        RDPR-only locks usually clear with minichlink -p.
        WRPR-only locks often ignore -p alone; cycling -P then -p forces a full
        option-byte rewrite (LinkE) and unlocks pages. -E alone does not clear WRPR.
        """
        print("Clearing flash protection (minichlink -p)...")

        def run_p_or_P(flag):
            cmd = self._minichlink_linke_cmd(minichlink, wch_linke_serial_number, flag)
            return subprocess.run(
                cmd, capture_output=True, text=True, timeout=60, input="\n")

        run_p_or_P("-p")
        time.sleep(0.3)

        if not self.set_3V3_power(False, wch_linke_serial_number):
            return False
        time.sleep(0.4)
        if not self.set_3V3_power(True, wch_linke_serial_number):
            return False
        time.sleep(0.25)
        if not self.test_tool.initailize(0.3):
            return False
        self._route_swio()

        if not self._option_bytes_write_protected(minichlink, wch_linke_serial_number):
            info = self._minichlink_detect_info(minichlink, wch_linke_serial_number)
            if info["detected"] and not info["rdp_enabled"]:
                print("Flash protection cleared")
                return True

        # WRPR page-protect: enable RDP then disable to force OB rewrite.
        print("WRPR still set; cycling -P then -p...")
        run_p_or_P("-P")
        time.sleep(0.4)
        run_p_or_P("-p")
        time.sleep(0.5)
        if not self.set_3V3_power(False, wch_linke_serial_number):
            return False
        time.sleep(0.4)
        if not self.set_3V3_power(True, wch_linke_serial_number):
            return False
        time.sleep(0.25)
        if not self.test_tool.initailize(0.3):
            return False
        self._route_swio()

        info = self._minichlink_detect_info(minichlink, wch_linke_serial_number)
        if not info["detected"]:
            print("CH32V003 not detected after clearing protection")
            return False
        if info["rdp_enabled"] or self._option_bytes_write_protected(
                minichlink, wch_linke_serial_number):
            print("Flash protection still active after -P/-p")
            return False
        print("Flash protection cleared")
        return True

    def _recover_protection_and_write(self, minichlink, firmware_path,
                                      wch_linke_serial_number=None):
        if not self._clear_flash_protection(minichlink, wch_linke_serial_number):
            return False
        ok, _ = self._write_firmware_image(
            minichlink, firmware_path, wch_linke_serial_number, halt=True)
        if not ok:
            print("Firmware flashing failed after clearing protection")
            return False
        print("Firmware written after clearing flash protection")
        return True

    def _recover_soft_brick_and_write(self, minichlink, firmware_path,
                                      wch_linke_serial_number=None, attempts=4):
        """Recover SDI-disabled DUT via NRST hold + 3V3 cycle, then halt+write.

        Critical: after releasing NRST, the *first* minichlink attach must be the
        write. A prior detect burns the boot window; clearing the matrix after
        release also loses the race to DisableSDI().
        """
        print("Trying NRST-hold power-cycle recovery...")
        tt = self.test_tool

        for attempt in range(1, attempts + 1):
            if not tt.initailize(0.5):
                return False

            if not tt.digital_write(0, 0, 0.2):
                print("Failed to drive NRST low")
                return False
            tt.connect_pins(tt.SSOP20_PIN4_MAP, tt.Y_305_PA0, 0.5)   # PD7 / NRST
            tt.connect_pins(tt.SSOP20_PIN18_MAP, tt.Y_305_PA7, 0.5)  # PD1 / SWIO
            tt.connect_pins(tt.WCH_LINKE_SWDIO, tt.Y_305_PA7, 0.5)
            tt.digital_write(0, 0, 0.1)

            if not self.set_3V3_power(False, wch_linke_serial_number):
                return False
            time.sleep(0.4)
            tt.digital_write(0, 0, 0.1)
            if not self.set_3V3_power(True, wch_linke_serial_number):
                return False
            time.sleep(0.15)

            # Optional mass-erase attempt while held (may no-op; still OK).
            subprocess.run(
                self._minichlink_linke_cmd(minichlink, wch_linke_serial_number, "-u"),
                capture_output=True, text=True, timeout=20)

            # Release NRST; keep SWIO routed — do not re-init the matrix here.
            tt.digital_write(0, 1, 0.02)

            if self._write_firmware_image(
                    minichlink, firmware_path, wch_linke_serial_number, halt=True)[0]:
                print("Firmware written after NRST power-cycle recovery")
                return True
            print(f"NRST recovery write failed (attempt {attempt}/{attempts})")

        print("Firmware flashing failed after NRST recovery")
        return False

    def flashFirmware(self, firmware_path, wch_linke_serial_number = None):
        #check if the firmware file exists
        if (not os.path.exists(firmware_path)):
            print("Firmware file not found: "+firmware_path)
            return False
        #check if the minichlink is ready in toolBinary folder
        minichlink = self.locateMinichlink()
        if (not minichlink):
            print("Minichlink not found")
            return False

        # Save user matrix, clear it, then route SWIO for programming only.
        # Without clear, existing PA7 links (e.g. PD0/X6) short the SWIO bus.
        if not self.test_tool.save_matrix(0.5):
            print("Failed to save matrix")
            return False
        if not self.test_tool.initailize(0.5):
            print("Failed to init matrix before flash")
            return False

        #for ch32v003, the SWIO is on PD1, pin 18 on TSSOP20 package
        #we can route the SWIO to on board WCH-LINKE SWDIO via any input gpio on CH32V305
        self._route_swio()

        ok = False
        try:
            # Argv list only — never shell=True (paths must not be interpreted by a shell).
            info = self._minichlink_detect_info(minichlink, wch_linke_serial_number)
            if not info["detected"]:
                # Option-byte changes often need a power reload before LinkE
                # can talk reliably again.
                print("CH32V003 target not found; power-cycling and retrying detect...")
                self.set_3V3_power(False, wch_linke_serial_number)
                time.sleep(0.4)
                self.set_3V3_power(True, wch_linke_serial_number)
                time.sleep(0.2)
                if not self.test_tool.initailize(0.3):
                    return False
                self._route_swio()
                info = self._minichlink_detect_info(minichlink, wch_linke_serial_number)

            if info["detected"]:
                protected = info["rdp_enabled"] or self._option_bytes_write_protected(
                    minichlink, wch_linke_serial_number)
                if protected:
                    # RDPR and/or WRPR option-byte lock.
                    ok = self._recover_protection_and_write(
                        minichlink, firmware_path, wch_linke_serial_number)
                else:
                    wrote, write_out = self._write_firmware_image(
                        minichlink, firmware_path, wch_linke_serial_number)
                    if wrote:
                        ok = True
                    else:
                        print("Firmware flashing failed")
                        # WRPR/RDPR can show up as Memory Protection Error even
                        # when the first detect line looked unlocked.
                        if "Memory Protection Error" in write_out or info["rdp_enabled"]:
                            ok = self._recover_protection_and_write(
                                minichlink, firmware_path, wch_linke_serial_number)
                        else:
                            if not self.test_tool.initailize(0.3):
                                return False
                            self._route_swio()
                            if self._option_bytes_write_protected(
                                    minichlink, wch_linke_serial_number):
                                ok = self._recover_protection_and_write(
                                    minichlink, firmware_path, wch_linke_serial_number)
            else:
                print("CH32V003 target not found")

            # Soft-brick (DisableSDI / PD1 reuse): NRST hold + 3V3 cycle, then halt+write.
            if not ok and not info["detected"]:
                ok = self._recover_soft_brick_and_write(
                    minichlink, firmware_path, wch_linke_serial_number)

            # Last chance: option-byte lock or SDI brick after a flaky first pass.
            if not ok:
                if not self.test_tool.initailize(0.3):
                    return False
                self._route_swio()
                info = self._minichlink_detect_info(minichlink, wch_linke_serial_number)
                if info["detected"] and (
                        info["rdp_enabled"]
                        or self._option_bytes_write_protected(
                            minichlink, wch_linke_serial_number)):
                    ok = self._recover_protection_and_write(
                        minichlink, firmware_path, wch_linke_serial_number)
                elif not info["detected"]:
                    ok = self._recover_soft_brick_and_write(
                        minichlink, firmware_path, wch_linke_serial_number)
        finally:
            # Clear SWIO hookup and restore the user's prior matrix connections.
            self.test_tool.initailize(0.5)
            if not self.test_tool.restore_matrix(0.5):
                print("Failed to restore matrix after flash")
                ok = False
        return ok

    def logic_analyzer_capture(self, rate_hz, sample_count, wait_for_input_time=1, during_capture=None):
        return self.test_tool.logic_analyzer_capture(
            rate_hz, sample_count, wait_for_input_time, during_capture)

    def logic_analyzer_capture_start(self, rate_hz, sample_count, wait_for_input_time=1):
        return self.test_tool.logic_analyzer_capture_start(rate_hz, sample_count, wait_for_input_time)

    def logic_analyzer_capture_poll(self, wait_for_input_time=0.1):
        return self.test_tool.logic_analyzer_capture_poll(wait_for_input_time)

    def logic_analyzer_capture_wait(self, sample_count=None, rate_hz=None,
                                      during_capture=None, poll_interval=0.001, timeout=30):
        return self.test_tool.logic_analyzer_capture_wait(
            sample_count, rate_hz, during_capture, poll_interval, timeout)

    def analog_capture(self, rate_hz, sample_count, channel_mask, wait_for_input_time=1,
                       during_capture=None):
        return self.test_tool.analog_capture(
            rate_hz, sample_count, channel_mask, wait_for_input_time, during_capture)

    def analog_capture_start(self, rate_hz, sample_count, channel_mask, wait_for_input_time=1):
        return self.test_tool.analog_capture_start(
            rate_hz, sample_count, channel_mask, wait_for_input_time)

    def analog_capture_poll(self, wait_for_input_time=0.1):
        return self.test_tool.analog_capture_poll(wait_for_input_time)

    def analog_capture_wait(self, sample_count=None, rate_hz=None, channel_mask=None,
                            during_capture=None, poll_interval=0.001, timeout=30):
        return self.test_tool.analog_capture_wait(
            sample_count, rate_hz, channel_mask, during_capture, poll_interval, timeout)

    def digital_write(self, pin, value, wait_for_input_time=0):
        return self.test_tool.digital_write(pin, value, wait_for_input_time)

    def send_command_batch(self, commands, flush=True):
        return self.test_tool.send_command_batch(commands, flush)

    def write_batch_wait_for_response(self, commands, string_to_wait, wait_for_input_time):
        return self.test_tool.write_batch_wait_for_response(
            commands, string_to_wait, wait_for_input_time)

    @staticmethod
    def digital_write_command(pin, value):
        return Ch32V305CCT6_test_tool.digital_write_command(pin, value)

    @staticmethod
    def build_digital_pulse_train(pin, pulse_count):
        return Ch32V305CCT6_test_tool.build_digital_pulse_train(pin, pulse_count)

    def set_3V3_power(self, on_off, wch_linke_serial_number = None):
        # minichlink -k3 -C linke / minichlink -kt -C linke
        minichlink = self.locateMinichlink()
        if (not minichlink):
            print("Minichlink not found")
            return False

        cmd = [minichlink, f"-k{'3' if on_off else 't'}", "-C", "linke"]
        if wch_linke_serial_number is not None:
            cmd.extend(["-l", str(wch_linke_serial_number)])
        result = subprocess.run(cmd, capture_output=True, text=True)
        out = (result.stdout or "") + (result.stderr or "")
        if "Skipping programmer initialization" not in out:
            print("Failed to set 3V3 power")
            return False
        return True

    def set_5V_power(self, on_off, wch_linke_serial_number = None):
        # minichlink -k5 -C linke / minichlink -kf -C linke
        minichlink = self.locateMinichlink()
        if (not minichlink):
            print("Minichlink not found")
            return False

        cmd = [minichlink, f"-k{'5' if on_off else 'f'}", "-C", "linke"]
        if wch_linke_serial_number is not None:
            cmd.extend(["-l", str(wch_linke_serial_number)])
        result = subprocess.run(cmd, capture_output=True, text=True)
        out = (result.stdout or "") + (result.stderr or "")
        if "Skipping programmer initialization" not in out:
            print("Failed to set 5V power")
            return False
        return True

    def debug_terminal_command(self, wch_linke_serial_number = None):
        # minichlink -d -C linke
        minichlink = self.locateMinichlink()
        if (not minichlink):
            print("Minichlink not found")
            return False

        command_minichlink = f"{minichlink} -d -C linke"
        if (wch_linke_serial_number is not None):
            command_minichlink = command_minichlink + f" -l {wch_linke_serial_number}"
        command_minichlink = command_minichlink + " -T"
        return command_minichlink
        