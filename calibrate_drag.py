from machine import Pin
import time
from hx711 import HX711

# Drag Load Cell Pins (GP14 = DOUT, GP15 = SCK)
drag_sensor = HX711(d_out=14, pd_sck=15)

print("Taring scale... Make sure nothing is touching the drag mount.")
time.sleep(1)
drag_sensor.tare(20)
print("Tare complete!")

print("\n--- DRAG CALIBRATION STEP ---")
print("1. Apply a known force/weight to the drag sensor (e.g., 20g).")
time.sleep(20)

raw_value = drag_sensor.get_value(20)
print(f"Raw Offset Value: {raw_value:.2f}")

# Enter your known calibration weight in grams
known_grams = 21.0  # Adjust this to match your test weight
scale_factor = raw_value / known_grams

print(f"\nYour calculated DRAG SCALE factor is: {scale_factor:.2f}")
print("Save this number to put into main.py!")

drag_sensor.set_scale(scale_factor)

# Test Loop
print("\nReading live calibrated drag values (Grams & Newtons):")
while True:
    grams = drag_sensor.get_units(3)
    newtons = (grams / 1000.0) * 9.81
    print(f"Drag: {grams:6.2f} g  |  {newtons:5.3f} N")
    time.sleep_ms(300)
