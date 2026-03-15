# Raspberry Pi Bluetooth Sync Project

## SSH Access


Pi A
```
ssh kangjun@192.168.50.13
```

Pi B
```
ssh kangjun2@192.168.50.4
```

Password
```
passwordis123
```

---

## Device Mapping

| Device | Username | Role |
|------|------|------|
| Raspberry Pi A | kangjun | Pi A (Scanner Trigger) |
| Raspberry Pi B | kangjun2 | Pi B (Listener / Sync Scanner) |

---

## Running the Project

Navigate to the project directory:

```
cd ble_sync_project
```

### Run Pi B First

```
sudo python3 pi_b_sync_scan.py
```

### Then Run Pi A

```
sudo python3 pi_a_sync_scan.py
```

---

## Project Structure

```
ble_sync_project/
│
├── pi_a_sync_scan.py   # Pi A scanning script
├── pi_b_sync_scan.py   # Pi B scanning script
└── README.md
```

---

## Notes

- Pi B must start **before** Pi A.
- Pi A sends the **synchronization trigger**.
- Both devices then **scan BLE signals and collect RSSI values**.
