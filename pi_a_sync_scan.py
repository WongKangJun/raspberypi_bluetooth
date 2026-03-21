import RPi.GPIO as GPIO
import time
from bluepy.btle import Scanner, DefaultDelegate

SYNC_PIN = 17

TX_POWER = -59
N = 2.0
D_AB = 0.50

#MODE = "discovery"
MODE = "track"

#TARGET_MAC = "aa:bb:cc:dd:ee:ff"
TARGET_MAC = "09:0d:9c:b4:fc:9b"

RSSI_WINDOW_SIZE = 3
STABILITY_THRESHOLD = 0.05
CONFIRM_COUNT = 2


def rssi_to_distance(rssi):
    return 10 ** ((TX_POWER - rssi) / (10 * N))


class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)


def decide_direction(current_distance, reference_distance, threshold):
    difference = current_distance - reference_distance

    if abs(difference) <= threshold:
        return "Stationary"
    elif difference < 0:
        return "Moving closer to Pi A"
    else:
        return "Moving away from Pi A"


GPIO.setmode(GPIO.BCM)
GPIO.setup(SYNC_PIN, GPIO.OUT, initial=GPIO.LOW)

print("Pi A sending sync in 2 seconds...")
time.sleep(2)

GPIO.output(SYNC_PIN, GPIO.HIGH)
time.sleep(0.5)
GPIO.output(SYNC_PIN, GPIO.LOW)

print("Sync sent to Pi B. Pi A scanning continuously now...")
print("Mode:", MODE)
print("Press Ctrl+C to stop.\n")

scanner = Scanner().withDelegate(ScanDelegate())
rssi_samples = []

reference_distance = None
candidate_state = None
candidate_count = 0
final_state = "Waiting for enough data"

try:
    while True:
        devices = scanner.scan(1.0)

        if MODE == "discovery":
            if len(devices) > 0:
                print("Pi A | Discovery results:")
                sorted_devices = sorted(devices, key=lambda d: d.rssi, reverse=True)

                for dev in sorted_devices:
                    print("  Device: %s | RSSI: %d dB" % (dev.addr, dev.rssi))
            else:
                print("Pi A | No BLE device detected in this scan window.")

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

                if reference_distance is None:
                    reference_distance = current_distance
                    final_state = "First reading"
                else:
                    new_state = decide_direction(
                        current_distance,
                        reference_distance,
                        STABILITY_THRESHOLD
                    )

                    if new_state == candidate_state:
                        candidate_count += 1
                    else:
                        candidate_state = new_state
                        candidate_count = 1

                    if candidate_count >= CONFIRM_COUNT:
                        final_state = candidate_state
                        reference_distance = current_distance

                print(
                    "Pi A | Device: %s | Latest RSSI: %d dB | Avg RSSI: %.2f dB | "
                    "dXA: %.2f m | dAB: %.2f m | Status: %s"
                    % (
                        chosen_device.addr,
                        chosen_device.rssi,
                        avg_rssi,
                        current_distance,
                        D_AB,
                        final_state
                    )
                )
            else:
                print("Pi A | Target MAC not detected in this scan window.")

except KeyboardInterrupt:
    print("\nPi A stopped by user.")

finally:
    GPIO.output(SYNC_PIN, GPIO.LOW)
    GPIO.cleanup()
