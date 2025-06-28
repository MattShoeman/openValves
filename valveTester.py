#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
from config import VALVE_PINS as RELAY_PINS, GARDEN_MASTER_PIN, VALVE_NAMES as ZONE_NAMES

# Configuration
#RELAY_PINS = [4, 25, 24, 23, 22, 17, 27]  # Subzone pins
#GARDEN_MASTER_PIN = 18  # Master valve pin
#ZONE_NAMES = ["Patio", "Garden-Berries", "Garden-Flowers", "Garden-Beds", "Garden-Tomatoes", "Fig", "Apple"]
TEST_DURATION = 20  # seconds for valve test

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    for pin in RELAY_PINS + [GARDEN_MASTER_PIN]:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.HIGH)  # Start with all relays OFF

def test_zone(zone_index):
    pin = RELAY_PINS[zone_index]
    print(f"\nTesting {ZONE_NAMES[zone_index]} (GPIO {pin})...")
    
    # For garden subzones (indices 1-4), activate master valve first
    if 1 <= zone_index <= 4:
        GPIO.output(GARDEN_MASTER_PIN, GPIO.LOW)
        print("Master Garden Valve ON")
        time.sleep(0.5)
    
    GPIO.output(pin, GPIO.LOW)  # Relay ON
    print(f"Valve OPEN - waiting {TEST_DURATION} seconds")
    time.sleep(TEST_DURATION)
    
    GPIO.output(pin, GPIO.HIGH)  # Relay OFF
    print("Valve CLOSED")
    
    # For garden subzones, turn off master valve
    if 1 <= zone_index <= 4:
        GPIO.output(GARDEN_MASTER_PIN, GPIO.HIGH)
        print("Master Garden Valve OFF")

def main_menu():
    print("\n=== Irrigation Valve Tester ===")
    for i, name in enumerate(ZONE_NAMES):
        print(f"{i+1}. Test {name} (GPIO {RELAY_PINS[i]})")
    print("8. Test ALL zones sequentially")
    print("0. Exit")
    
    while True:
        try:
            choice = int(input("\nSelect zone to test (0-8): "))
            if 1 <= choice <= 7:
                test_zone(choice-1)
            elif choice == 8:
                for i in range(7):
                    test_zone(i)
            elif choice == 0:
                break
            else:
                print("Invalid choice. Enter 0-8")
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
