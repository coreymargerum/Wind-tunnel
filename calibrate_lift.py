from machine import Pin
import time
from hx711 import HX711

# Lift Load Cell Pins (Planned layout)[cite: 3]
lift_sensor = HX711(d_out=12, pd_sck=13)

print("Taring scale... Make sure nothing is resting on the lift balance.")
time.sleep(1)
lift_sensor.tare(20)
print("Tare complete!")

print("\n--- CALIBRATION STEP ---")
print("1. Place a known weight on the lift sensor (e.g., 100g).")
time.sleep(20)

raw_value = lift_sensor.get_value(20)
print(f"Raw Offset Value: {raw_value:.2f}")

# Enter your known weight in grams or Newtons to calculate scale factor
known_grams = 214.0  # Change this to match your physical object
scale_factor = raw_value / known_grams

print(f"\nYour calculated SCALE factor is: {scale_factor:.2f}")
print("Save this number to use in main.py!")

lift_sensor.set_scale(scale_factor)

# Test Loop
print("\nReading live calibrated values (Grams):")
while True:
    grams = lift_sensor.get_units(3)
    newtons = (grams / 1000.0) * 9.81
    print(f"Lift: {grams:6.1f} g  |  {newtons:5.2f} N")
    time.sleep_ms(300)
