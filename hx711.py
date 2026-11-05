import time
from machine import Pin

class HX711:
    def __init__(self, d_out, pd_sck, gain=128):
        self.d_out = Pin(d_out, Pin.IN)
        self.pd_sck = Pin(pd_sck, Pin.OUT, value=0)
        self.GAIN = 0
        self.OFFSET = 0
        self.SCALE = 1.0
        self.set_gain(gain)

    def set_gain(self, gain=128):
        if gain == 128:
            self.GAIN = 1
        elif gain == 64:
            self.GAIN = 3
        elif gain == 32:
            self.GAIN = 2
        self.read()

    def is_ready(self):
        return self.d_out.value() == 0

    def read(self):
        while not self.is_ready():
            time.sleep_us(10)

        raw = 0
        for _ in range(24):
            self.pd_sck.value(1)
            time.sleep_us(1)
            raw = (raw << 1) | self.d_out.value()
            self.pd_sck.value(0)
            time.sleep_us(1)

        # Set gain for next reading
        for _ in range(self.GAIN):
            self.pd_sck.value(1)
            time.sleep_us(1)
            self.pd_sck.value(0)
            time.sleep_us(1)

        # Convert 24-bit 2's complement
        if raw & 0x800000:
            raw -= 0x1000000

        return raw

    def read_average(self, times=10):
        sum_vals = 0
        for _ in range(times):
            sum_vals += self.read()
        return sum_vals / times

    def tare(self, times=15):
        """Sets the zero offset based on current load."""
        self.OFFSET = self.read_average(times)

    def set_scale(self, scale):
        """Sets calibration factor (raw_units / weight_in_grams or Newtons)."""
        self.SCALE = scale

    def get_value(self, times=5):
        """Returns raw offset-adjusted reading."""
        return self.read_average(times) - self.OFFSET

    def get_units(self, times=5):
        """Returns calibrated weight/force."""
        return self.get_value(times) / self.SCALE
