import framebuf
import time
from machine import I2C, Pin
from sh1107 import SH1107
from sh1107 import SH1107_I2C

i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)
oled = SH1107_I2C(
    128,
    128,
    i2c,
    address=0x3C,
    rotate=180,
    external_vcc=False,
    delay_ms=200
)

from machine import I2C, Pin

i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)

print("I2C devices found:", [hex(addr) for addr in i2c.scan()])

CELL_W, CELL_H = 42, 32
items = [
    "Fan1", "Fan2", "Fan3", 
    "Fan4", "Fan5", "Fan6", 
    "Fan7", "Fan8", "Fan9", 
    "All",  "Cor",  "Edg"
]

CORNER_INDICES = [0, 2, 8, 6]   # Fans 1, 3, 5, 7
EDGE_INDICES   = [1, 3, 5, 7]   # Fans 2, 4, 6, 8
ALL_FAN_INDICES = list(range(9)) # Fans 1 through 9

# --- SAFETY MEASURE 1: Start Target Values at 0% ---
target_rpms = [0] * 12
actual_rpms = [0.0] * 12  # Tracks smoothly ramped real-time values

# --- Hardware Pins ---
pin_clk = Pin(7, Pin.IN, Pin.PULL_UP)
pin_dt  = Pin(8, Pin.IN, Pin.PULL_UP)
pin_sw  = Pin(9, Pin.IN, Pin.PULL_UP)
btn     = Pin(14, Pin.IN, Pin.PULL_UP)

# --- Global States ---
selected_item = 0
is_editing = False      # False = Browsing, True = Editing
screen = 1
needs_redraw = True

last_clk = pin_clk.value()
last_ramp_time = time.ticks_ms()

# Configuration for safety acceleration ramp
RAMP_STEP = 5.0          # Max % speed change per ramp tick
RAMP_INTERVAL_MS = 100   # Milliseconds between ramp steps

# --- Safety Acceleration Ramp Function ---
def update_fan_ramps():
    """Smoothly ramps actual fan speeds toward target settings."""
    global last_ramp_time, needs_redraw
    now = time.ticks_ms()
    
    if time.ticks_diff(now, last_ramp_time) >= RAMP_INTERVAL_MS:
        ramp_changed = False
        for i in range(12):
            if actual_rpms[i] < target_rpms[i]:
                # Accelerate safely
                actual_rpms[i] = min(target_rpms[i], actual_rpms[i] + RAMP_STEP)
                ramp_changed = True
            elif actual_rpms[i] > target_rpms[i]:
                # Decelerate (instant or ramped, currently matches ramp rate)
                actual_rpms[i] = max(target_rpms[i], actual_rpms[i] - RAMP_STEP)
                ramp_changed = True
                
        if ramp_changed:
            needs_redraw = True
        last_ramp_time = now

# --- Target Value Updating Logic ---
def update_target_rpm(target_idx, direction):
    """Updates target values (0-100%) for fans or groups."""
    step = direction * 5
    
    if target_idx < 9:
        # Individual Fan
        new_val = target_rpms[target_idx] + step
        target_rpms[target_idx] = max(0, min(100, new_val))
    elif target_idx == 9:
        # "All" - Fans 1 to 9
        new_val = target_rpms[9] + step
        target_rpms[9] = max(0, min(100, new_val))
        for idx in ALL_FAN_INDICES:
            target_rpms[idx] = target_rpms[9]
    elif target_idx == 10:
        # "Cor" - Corner Fans (1, 3, 5, 7)
        new_val = target_rpms[10] + step
        target_rpms[10] = max(0, min(100, new_val))
        for idx in CORNER_INDICES:
            target_rpms[idx] = target_rpms[10]
    elif target_idx == 11:
        # "Edg" - Edge Fans (2, 4, 6, 8)
        new_val = target_rpms[11] + step
        target_rpms[11] = max(0, min(100, new_val))
        for idx in EDGE_INDICES:
            target_rpms[idx] = target_rpms[11]

# --- KY-040 Encoder ---
last_clk = pin_clk.value()
last_encoder_time = time.ticks_ms()

ENCODER_DEBOUNCE_MS = 3

def encoder_isr(pin):
    global selected_item, is_editing
    global last_clk, last_encoder_time, needs_redraw

    current_clk = pin_clk.value()

    # Only process a HIGH-to-LOW transition
    if last_clk == 1 and current_clk == 0:
        now = time.ticks_ms()

        # Ignore contact bounce
        if time.ticks_diff(now, last_encoder_time) >= ENCODER_DEBOUNCE_MS:
            last_encoder_time = now

            if screen == 1:
                # Reverse direction from the original code
                direction = -1 if pin_dt.value() != current_clk else 1

                if is_editing:
                    update_target_rpm(selected_item, direction)
                else:
                    selected_item = (selected_item + direction) % 12

                needs_redraw = True

    last_clk = current_clk

pin_clk.irq(
    trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING,
    handler=encoder_isr
)


# --- Drawing Functions ---
def draw_menu_rpm():
    oled.fill(0)
    for i in range(12):
        col = i % 3
        row = i // 3
        x = col * CELL_W
        y = row * CELL_H
        
        is_selected = (i == selected_item)
        # Display the current actual ramped speed
        disp_val = int(actual_rpms[i])
        
        if is_selected and is_editing:
            # EDIT MODE: Solid white background block
            oled.fill_rect(x, y, CELL_W, CELL_H, 1)
            oled.text(items[i], x + 3, y + 3, 0)
            oled.text(f"{disp_val}%", x + 10, y + 14, 0)
        elif is_selected:
            # BROWSE MODE: Thick border
            oled.rect(x, y, CELL_W, CELL_H, 1)
            oled.rect(x + 1, y + 1, CELL_W - 2, CELL_H - 2, 1)
            oled.text(items[i], x + 3, y + 3, 1)
            oled.text(f"{disp_val}%", x + 10, y + 14, 1)
        else:
            # UNSELECTED BOX
            oled.rect(x, y, CELL_W, CELL_H, 1)
            oled.text(items[i], x + 3, y + 3, 1)
            oled.text(f"{disp_val}%", x + 10, y + 14, 1)

    oled.show()

Batterys = ["Bat1", "Bat2", "Bat3"]

def draw_menu_batt(Batt, drag, lift, Air_sp, REC):
    oled.fill(0)
    for i in range(3):
        x = i * 42
        oled.rect(x, 5, CELL_W, 25, 1)
        oled.text(Batterys[i], x + 3, 7, 1)
        oled.text(f"{Batt}V", x + 3, 18, 1)

    oled.text(f'Drag {drag}N', 0, 35, 1)
    oled.text(f'Lift {lift}N', 3, 50, 1)
    oled.text(f'Air Speed {Air_sp}M/S', 3, 65, 1)
    oled.text(f'REC* Data:{REC}', 3, 100, 1)
    oled.show()

# --- Initial Draw ---
draw_menu_rpm()

last_sw_state = 1
last_btn_state = 1

# --- Main Program Loop ---
while True:
    # 1. Update acceleration ramps
    update_fan_ramps()

    # 2. Polling for Encoder Switch (GP9)
    sw_val = pin_sw.value()
    if last_sw_state == 1 and sw_val == 0:
        if screen == 1:
            is_editing = not is_editing
            needs_redraw = True
        time.sleep_ms(150)
    last_sw_state = pin_sw.value()

    # 3. Polling for Screen Toggle Button (GP14)
    btn_val = btn.value()
    if last_btn_state == 1 and btn_val == 0:
        if screen == 1:
            screen = 2
            is_editing = False
        else:
            screen = 1
        needs_redraw = True
        time.sleep_ms(150)
    last_btn_state = btn.value()

    # 4. Refresh OLED Display
    if needs_redraw:
        if screen == 1:
            draw_menu_rpm()
        else:
            draw_menu_batt(3.3, 6.8, 1.4, 12, 'YES')
        needs_redraw = False

    time.sleep_ms(10)
