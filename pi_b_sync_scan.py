import RPi.GPIO as GPIO
import time
from bluepy.btle import Scanner, DefaultDelegate

SYNC_PIN = 17   # GPIO pin

TX_POWER = -59
N = 2.0
D_AB = 0.50   # distance between Pi A and Pi B in metres

#MODE = "track"
#MODE = "discovery"

#TARGET_MAC = "aa:bb:cc:dd:ee:ff"
TARGET_MAC = "09:0d:9c:b4:fc:9b"

RSSI_WINDOW_SIZE = 5
STABILITY_THRESHOLD = 0.15   # metres
MOVEMENT_COOLDOWN = 1        # number of loops before updating state


def rssi_to_distance(rssi):
    return 10 ** ((TX_POWER - rssi) / (10 * N))


class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)


def classify_movement(previous_distance, current_distance, threshold):
    if previous_distance is None:
        return "First reading"

    difference = current_distance - previous_distance

    if abs(difference) < threshold:
        return "Stationary"
    elif difference < 0:
        return "Moving closer to Pi B"
    else:
        return "Moving away from Pi B"


GPIO.setmode(GPIO.BCM)
GPIO.setup(SYNC_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

print("Pi B waiting for sync from Pi A...")

while GPIO.input(SYNC_PIN) == GPIO.HIGH:
    pass

while GPIO.input(SYNC_PIN) == GPIO.LOW:
    pass

print("Sync received from Pi A. Pi B scanning continuously now...")
print("Mode:", MODE)
print("Press Ctrl+C to stop.\n")

scanner = Scanner().withDelegate(ScanDelegate())
rssi_samples = []
previous_distance = None
stable_counter = 0

try:
    while True:
        devices = scanner.scan(1.0)

        if MODE == "discovery":
            if len(devices) > 0:
                print("Pi B | Discovery results:")
                sorted_devices = sorted(devices, key=lambda d: d.rssi, reverse=True)

                for dev in sorted_devices:
                    print("  Device: %s | RSSI: %d dB" % (dev.addr, dev.rssi))
            else:
                print("Pi B | No BLE device detected in this scan window.")

        elif MODE == "track":
            chosen_device = None

            for dev in devices:
                if dev.addr.lower() == TARGET_MAC.lower():
                    chosen_device = dev
                    break

            if chosen_device is not None:
                rssi_samples.append(chosen_device.rssi)

                if len(rssi_samples) > RSSI_WINDOW_SIZE:
                    rssi_samples.pop(0)

                avg_rssi = sum(rssi_samples) / len(rssi_samples)
                current_distance = rssi_to_distance(avg_rssi)

                movement_state = classify_movement(
                    previous_distance,
                    current_distance,
                    STABILITY_THRESHOLD
                )

                if movement_state == "Stationary":
                    stable_counter += 1
                else:
                    stable_counter = 0

                if stable_counter >= MOVEMENT_COOLDOWN:
                    final_state = "Stationary"
                else:
                    final_state = movement_state

                print(
                    "Pi B | Device: %s | Latest RSSI: %d dB | Avg RSSI: %.2f dB | "
                    "dXB: %.2f m | dAB: %.2f m | Status: %s"
                    % (
                        chosen_device.addr,
                        chosen_device.rssi,
                        avg_rssi,
                        current_distance,
                        D_AB,
                        final_state
                    )
                )

                previous_distance = current_distance

            else:
                print("Pi B | Target MAC not detected in this scan window.")

except KeyboardInterrupt:
    print("\nPi B stopped by user.")

finally:
    GPIO.cleanup()
