import RPi.GPIO as GPIO
import time
from bluepy.btle import Scanner, DefaultDelegate

SYNC_PIN = 17

TX_POWER = -59
N = 2.0

# change to "track" later, once done default change to "track"
MODE = "discovery"   
#MODE= "track"

TARGET_MAC = "aa:bb:cc:dd:ee:ff"
#TARGET_MAC = "09:f6:70:f0:d2:32"   
# replace real MAC address when using track mode
# TARGET_MAC= "40:23:43:d3:36:82", once done change back to "aa:bb:cc:dd:ee:ff"  


def rssi_to_distance(rssi):
    return 10 ** ((TX_POWER - rssi) / (10 * N))


class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)


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

try:
    while True:
        devices = scanner.scan(1.0)

        if MODE == "discovery":
            if len(devices) > 0:
                print("Pi A | Discovery results:")
                for dev in devices:
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
                avg_rssi = sum(rssi_samples) / len(rssi_samples)
                est_distance = rssi_to_distance(avg_rssi)

                print(
                    "Pi A | Device: %s | Latest RSSI: %d dB | Avg RSSI: %.2f dB | Est distance: %.2f m"
                    % (chosen_device.addr, chosen_device.rssi, avg_rssi, est_distance)
                )
            else:
                print("Pi A | Target MAC not detected in this scan window.")

except KeyboardInterrupt:
    print("\nPi A stopped by user.")

finally:
    GPIO.output(SYNC_PIN, GPIO.LOW)
    GPIO.cleanup()
