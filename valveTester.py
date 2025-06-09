#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

# Configuration
RELAY_PINS = [17, 18, 27, 22]  # Update these to match your GPIO pins
ZONE_NAMES = ["Patio", "Flowers", "Fig", "Apple"]
TEST_DURATION = 20  # seconds for valve test

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    for pin in RELAY_PINS:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.HIGH)  # Start with all relays OFF

def test_zone(zone_index):
    pin = RELAY_PINS[zone_index]
    print(f"\nTesting {ZONE_NAMES[zone_index]} (GPIO {pin})...")
    
    GPIO.output(pin, GPIO.LOW)  # Relay ON
    print(f"Valve OPEN - waiting {TEST_DURATION} seconds")
    time.sleep(TEST_DURATION)
    
    GPIO.output(pin, GPIO.HIGH)  # Relay OFF
    print("Valve CLOSED")

def main_menu():
    print("\n=== Irrigation Valve Tester ===")
    for i, name in enumerate(ZONE_NAMES):
        print(f"{i+1}. Test {name} (GPIO {RELAY_PINS[i]})")
    print("5. Test ALL zones sequentially")
    print("0. Exit")
    
    while True:
        try:
            choice = int(input("\nSelect zone to test (0-5): "))
            if 1 <= choice <= 4:
                test_zone(choice-1)
            elif choice == 5:
                for i in range(4):
                    test_zone(i)
            elif choice == 0:
                break
            else:
                print("Invalid choice. Enter 0-5")
        except ValueError:
            print("Please enter a number")
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    try:
        setup_gpio()
        main_menu()
    finally:
        GPIO.cleanup()
        print("\nGPIO cleanup complete. Exiting.")
