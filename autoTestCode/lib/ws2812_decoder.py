# WS2812 / WS281x decoder for logic-analyzer sample streams.
# State machine aligned with libsigrokdecode decoders/rgb_led_ws281x/pd.py

from dataclasses import dataclass

WIRE_ORDERS = ("BGR", "BRG", "GBR", "GRB", "RBG", "RGB", "RWBG", "RGBW")
TEXT_ORDERS = ("wire", "RGB[W]", "RGB", "RGBW", "RGWB", "BGR", "BRG", "GBR", "GRB", "RBG")


@dataclass
class Ws2812Bit:
    value: int
    start: int
    end: int


@dataclass
class Ws2812Reset:
    start: int
    end: int


@dataclass
class Ws2812DecodeResult:
    pixels: list
    bits: list
    resets: list


def _wire_components(wire_order):
    order = wire_order.upper()
    if (order not in WIRE_ORDERS):
        raise ValueError(f"wire_order must be one of {WIRE_ORDERS}")
    return [c for c in order if c in "RGBW"]


def _text_format(text_order):
    order = text_order.lower()
    if (order == "wire"):
        return "wire"
    if (order == "rgb[w]"):
        return "#{r:02x}{g:02x}{b:02x}{wt:s}"
    formats = {
        "bgr": "#{b:02x}{g:02x}{r:02x}",
        "brg": "#{b:02x}{r:02x}{g:02x}",
        "gbr": "#{g:02x}{b:02x}{r:02x}",
        "grb": "#{g:02x}{r:02x}{b:02x}",
        "rbg": "#{r:02x}{b:02x}{g:02x}",
        "rgb": "#{r:02x}{g:02x}{b:02x}",
        "rgbw": "#{r:02x}{g:02x}{b:02x}{w:02x}",
        "rgwb": "#{r:02x}{g:02x}{w:02x}{b:02x}",
    }
    text_format = formats.get(order)
    if (text_format is None):
        raise ValueError(f"text_order must be one of {TEXT_ORDERS}")
    return text_format


def _component_to_pixel(values, components):
    rgbw = {"R": 0, "G": 0, "B": 0, "W": 0}
    for component, value in zip(components, values):
        rgbw[component] = value
    if ("W" in components):
        return (rgbw["R"], rgbw["G"], rgbw["B"], rgbw["W"])
    return (rgbw["R"], rgbw["G"], rgbw["B"])


def _append_bit(bits, bit_value, wire_components, pixels):
    bits.append(bit_value)
    need_bits = len(wire_components) * 8
    if (len(bits) < need_bits):
        return
    values = []
    for index in range(len(wire_components)):
        byte_value = 0
        for bit_index in range(8):
            byte_value = (byte_value << 1) | bits[index * 8 + bit_index]
        values.append(byte_value)
    pixels.append(_component_to_pixel(values, wire_components))
    bits.clear()


def format_pixel_text(pixel, wire_order="GRB", text_order="RGB[W]"):
    components = _wire_components(wire_order)
    text_format = _text_format(text_order)
    if (len(pixel) == 3):
        r, g, b = pixel
        w = None
    else:
        r, g, b, w = pixel
    wt = "" if w is None else f"{w:02x}"
    if (text_format == "wire"):
        comp_values = {}
        for component in components:
            comp_values[component.lower()] = {
                "R": r, "G": g, "B": b, "W": w if w is not None else 0,
            }[component]
        return "#" + "".join(f"{comp_values[c.lower()]:02x}" for c in components)
    return text_format.format(r=r, g=g, b=b, w=w if w is not None else 0, wt=wt)


def pixels_between_resets(result, wire_order="GRB", first_reset_index=0):
    """Pixels whose bits lie entirely between two consecutive reset pulses."""
    bits_per_pixel = len(_wire_components(wire_order)) * 8
    if (first_reset_index + 1 >= len(result.resets)):
        return []

    frame_start = result.resets[first_reset_index].end
    frame_end = result.resets[first_reset_index + 1].start
    frame_pixels = []

    for pixel_index, pixel in enumerate(result.pixels):
        bit_base = pixel_index * bits_per_pixel
        if (bit_base + bits_per_pixel > len(result.bits)):
            break
        first_bit = result.bits[bit_base]
        last_bit = result.bits[bit_base + bits_per_pixel - 1]
        if (first_bit.start >= frame_end):
            break
        if (first_bit.start >= frame_start and first_bit.start < frame_end):
            frame_pixels.append(pixel)

    return frame_pixels


def decode_ws2812(samples, rate_hz, wire_order="GRB", reset_min_us=50.0):
    if (rate_hz <= 0 or len(samples) == 0):
        return Ws2812DecodeResult([], [], [])

    wire_components = _wire_components(wire_order)
    samples_625ns = int(rate_hz * 625e-9)
    samples_50us = round(rate_hz * reset_min_us * 1e-6)
    reset_skip = samples_50us + 1

    start = 0
    while (start < len(samples) and samples[start] != 0):
        start += 1
    if (start >= len(samples)):
        return Ws2812DecodeResult([], [], [])

    bits = []
    pixels = []
    bit_events = []
    reset_events = []

    ss_bit = None
    inv_bit = start
    es_bit = None
    check_reset = False

    def handle_bit(ss, es, value):
        bit_events.append(Ws2812Bit(value, ss, es))
        _append_bit(bits, value, wire_components, pixels)

    def handle_reset(ss_rst, es_rst):
        nonlocal ss_bit, inv_bit, es_bit, check_reset
        es_bit = inv_bit
        if (ss_bit is not None and inv_bit is not None and es_bit is not None):
            duty = inv_bit - ss_bit
            thres = samples_625ns
            if (bit_events):
                period = bit_events[-1].end - bit_events[-1].start
                thres = period * 0.5
            bit_value = 1 if duty >= thres else 0
            handle_bit(ss_bit, inv_bit, bit_value)

        reset_events.append(Ws2812Reset(ss_rst, es_rst))
        check_reset = False
        bits.clear()
        ss_bit = None
        inv_bit = None
        es_bit = None

    for index in range(start + 1, len(samples)):
        sample = samples[index]
        prev = samples[index - 1]
        rising = (prev == 0 and sample == 1)
        falling = (prev == 1 and sample == 0)

        if (check_reset and sample == 0 and inv_bit is not None):
            if (index - inv_bit >= reset_skip):
                handle_reset(inv_bit, index)
                continue

        if (rising):
            check_reset = False
            if (ss_bit is not None and inv_bit is not None):
                es_bit = index
                period = es_bit - ss_bit
                duty = inv_bit - ss_bit
                if (period > 0):
                    bit_value = 1 if (duty / period) > 0.5 else 0
                    handle_bit(ss_bit, es_bit, bit_value)
            ss_bit = index
            inv_bit = None
            es_bit = None

        if (falling):
            check_reset = True
            inv_bit = index

    if (check_reset and inv_bit is not None):
        end_index = len(samples) - 1
        if (samples[end_index] == 0 and end_index - inv_bit >= reset_skip):
            handle_reset(inv_bit, end_index)

    return Ws2812DecodeResult(pixels, bit_events, reset_events)


def _encode_bit(samples, rate_hz, bit_value, bit_time_us=1.2):
    bit_samples = max(4, int(rate_hz * bit_time_us * 1e-6))
    high_samples = int(bit_samples * (0.70 if bit_value else 0.30))
    low_samples = bit_samples - high_samples
    samples.extend([1] * high_samples)
    samples.extend([0] * low_samples)


def _encode_pixel(samples, rate_hz, g, r, b, wire_order="GRB", w=None):
    component_values = {"G": g, "R": r, "B": b, "W": w if w is not None else 0}
    for component in _wire_components(wire_order):
        value = component_values[component]
        for shift in range(7, -1, -1):
            _encode_bit(samples, rate_hz, (value >> shift) & 1)


def _self_test():
    rate_hz = 10_000_000
    samples = []
    _encode_pixel(samples, rate_hz, 0x12, 0x34, 0x56, "GRB")
    _encode_pixel(samples, rate_hz, 0x00, 0xFF, 0x00, "GRB")
    reset_samples = int(rate_hz * 60e-6)
    samples.extend([0] * reset_samples)
    _encode_pixel(samples, rate_hz, 0xAA, 0xBB, 0xCC, "GRB")

    result = decode_ws2812(samples, rate_hz, wire_order="GRB", reset_min_us=50.0)
    assert len(result.resets) >= 1, f"expected reset, got {len(result.resets)}"
    assert len(result.pixels) >= 3, f"expected >=3 pixels, got {len(result.pixels)}"
    assert result.pixels[0] == (0x34, 0x12, 0x56), result.pixels[0]
    assert result.pixels[1][0] == 0xFF and result.pixels[1][1] == 0x00, result.pixels[1]
    assert result.pixels[2] == (0xBB, 0xAA, 0xCC), result.pixels[2]
    assert len(result.bits) >= 72, f"expected >=72 bits, got {len(result.bits)}"
    assert format_pixel_text(result.pixels[0], "GRB", "RGB[W]") == "#341256"

    rgbw_samples = []
    _encode_pixel(rgbw_samples, rate_hz, 0x11, 0x22, 0x33, "RGBW", w=0x44)
    rgbw_result = decode_ws2812(rgbw_samples, rate_hz, wire_order="RGBW")
    assert rgbw_result.pixels[0] == (0x22, 0x11, 0x33, 0x44), rgbw_result.pixels[0]

    mid_bit_samples = [1] * 5 + samples
    mid_bit_result = decode_ws2812(mid_bit_samples, rate_hz, wire_order="GRB")
    assert len(mid_bit_result.pixels) >= 3, "initial-high capture should sync on first low"

    print("ws2812_decoder self-test passed")


if __name__ == "__main__":
    _self_test()
