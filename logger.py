import csv
import datetime
import time
import serial

PORT = "/dev/tty.usbmodem1301"
BAUD_RATE = 115200

# 1. Ask the user before opening the port
user_input = input("Type 'start' and press Enter to connect to Pico: ")

if user_input.strip().lower() == "start":
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    csv_filename = f"wind_tunnel_log_{timestamp_str}.csv"

    try:
        # Open serial port
        ser = serial.Serial(PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        print(f"\nConnected to {PORT}!")
        print(f"Saving data to '{csv_filename}'")
        print("Press the physical LOG button (GP19) on your hardware to start sending data.")
        print("Press Ctrl+C in this terminal at any time to disconnect cleanly for Thonny.\n")

        with open(csv_filename, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Pico_Timestamp_ms", "Lift_N", "Drag_N", "Airspeed_m_s"])

            while True:
                if ser.in_waiting > 0:
                    line = ser.readline().decode("utf-8", errors="ignore").strip()

                    # Filter out non-data status lines
                    if not line or "LOGGING" in line or "Timestamp" in line or "I2C" in line:
                        print(f"Pico Status: {line}")
                        continue

                    # Process 4-value CSV rows (time, lift, drag, airspeed)
                    parts = line.split(",")
                    if len(parts) == 4:
                        try:
                            pico_ms = int(parts[0])
                            lift_n = float(parts[1])
                            drag_n = float(parts[2])
                            speed_ms = float(parts[3])

                            writer.writerow([pico_ms, lift_n, drag_n, speed_ms])
                            file.flush()

                            print(f"Saved: {pico_ms}ms | Lift: {lift_n}N | Drag: {drag_n}N | Speed: {speed_ms}m/s")
                        except ValueError:
                            pass

    except KeyboardInterrupt:
        print("\nDisconnecting...")
    except serial.SerialException as e:
        print(f"\nCould not open port: {e}")
        print("Make sure Thonny is closed or disconnected first!")
    finally:
        # 2. Always close the port cleanly when exiting
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial connection CLOSED. You can now use Thonny.")
else:
    print("Cancelled.")
