import time
import math

class MS4525DO:
    def __init__(self, i2c, address=0x28, p_min=-1.0, p_max=1.0, rho=1.225):
        """
        :param i2c: Configured machine.I2C object
        :param address: Sensor I2C address (default 0x28)
        :param p_min: Minimum differential pressure rating in PSI (e.g. -1.0 PSI for 1PSI sensor)
        :param p_max: Maximum differential pressure rating in PSI (e.g. +1.0 PSI)
        :param rho: Air density in kg/m^3 (Standard sea-level air = 1.225 kg/m^3)
        """
        self.i2c = i2c
        self.address = address
        self.p_min = p_min
        self.p_max = p_max
        self.rho = rho
        self.offset_pa = 0.0  # Zero-offset calibration in Pascals

    def read_raw(self):
        """Reads 4 bytes from the sensor: 2 bytes pressure, 2 bytes temperature."""
        try:
            data = self.i2c.readfrom(self.address, 4)
        except Exception as e:
            return None, None, None

        # Status bits (bits 7-6 of byte 0)
        status = (data[0] & 0xC0) >> 6

        # 14-bit raw pressure value
        raw_p = ((data[0] & 0x3F) << 8) | data[1]

        # 11-bit raw temperature value
        raw_t = ((data[2] << 8) | (data[3] & 0xE0)) >> 5

        return status, raw_p, raw_t

    def read_pressure_pa(self):
        """Converts raw readings to differential pressure in Pascals."""
        status, raw_p, _ = self.read_raw()
        if raw_p is None or status == 3:  # Status 3 indicates fault/error
            return None

        # MS4525DO output range: 10% to 90% of 14-bit scale (1638 to 14745 counts)
        # Transfer function: P_psi = (raw_p - 1638) * (p_max - p_min) / (14745 - 1638) + p_min
        p_psi = (raw_p - 1638) * (self.p_max - self.p_min) / (14745 - 1638) + self.p_min

        # Convert PSI to Pascals (1 PSI = 6894.76 Pa)
        p_pa = p_psi * 6894.76

        return p_pa - self.offset_pa

    def zero_calibrate(self, samples=50):
        """Averages zero-flow pressure offset for calibration."""
        print("Calibrating airspeed zero offset... Keep wind tunnel off!")
        total = 0.0
        valid_samples = 0
        
        for _ in range(samples):
            p = self.read_pressure_pa()
            if p is not None:
                total += p
                valid_samples += 1
            time.sleep_ms(20)

        if valid_samples > 0:
            self.offset_pa += (total / valid_samples)
            print(f"Calibration complete. Offset: {self.offset_pa:.2f} Pa")
        else:
            print("Calibration failed: Could not read from sensor.")

    def get_airspeed(self):
        """Returns calculated airspeed in meters per second (m/s)."""
        p_pa = self.read_pressure_pa()
        if p_pa is None:
            return 0.0

        # Discard negative pressure noise or reverse flow
        if p_pa <= 0:
            return 0.0

        # Bernoulli's Equation: v = sqrt(2 * dp / rho)
        velocity = math.sqrt((2.0 * p_pa) / self.rho)
        return velocity
