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
TARGET_MAC = "36:56:e5:70:09:eb"

RSSI_WINDOW_SIZE = 5
STABILITY_THRESHOLD = 0.15
MOVEMENT_COOLDOWN = 1


def rssi_to_distance(rssi):
    return 10 ** ((TX_POWER - rssi) / (10 * N))

def get_filtered_rssi(rssi_samples):
    if len(rssi_samples) < 3:
        return sum(rssi_samples) / len(rssi_samples)

    sorted_samples = sorted(rssi_samples)

    if len(sorted_samples) >= 5:
        filtered_samples = sorted_samples[1:-1]
    else:
        filtered_samples = sorted_samples

    return sum(filtered_samples) / len(filtered_samples)

def get_confidence_info(rssi_samples):
    if len(rssi_samples) < 3:
        return 50, "Warming up"

    sorted_samples = sorted(rssi_samples)

    # Remove one extreme low and one extreme high sample
    # so one noisy RSSI reading does not crash confidence
    if len(sorted_samples) >= 5:
        filtered_samples = sorted_samples[1:-1]
    else:
        filtered_samples = sorted_samples

    spread = max(filtered_samples) - min(filtered_samples)

    confidence_percent = max(40, min(100, int(100 - (spread * 10))))

    if confidence_percent >= 75:
        confidence_label = "High"
    elif confidence_percent >= 45:
        confidence_label = "Medium"
    else:
        confidence_label = "Low"

    return confidence_percent, confidence_label


class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)


def classify_movement(previous_distance, current_distance, threshold):
    if previous_distance is None:
        return "Initalizing"

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
final_state = "Waiting for enough data"

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

                avg_rssi = get_filtered_rssi(rssi_samples)
                current_distance = rssi_to_distance(avg_rssi)

                confidence_percent, confidence_label = get_confidence_info(rssi_samples)

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
                    "dXB: %.2f m | dAB: %.2f m | Status: %s | Confidence: %s (%d%%)"
                    % (
                        chosen_device.addr,
                        chosen_device.rssi,
                        avg_rssi,
                        current_distance,
                        D_AB,
                        final_state,
                        confidence_label,
                        confidence_percent
                    )
                )

                previous_distance = current_distance

            else:
                print("Pi B | Target MAC not detected in this scan window.")

except KeyboardInterrupt:
    print("\nPi B stopped by user.")

finally:
    GPIO.cleanup()
