import serialData
import os

test_array = bytearray(os.urandom(10000))

serial_interface1 = serialData.SerialInterface("/dev/tty.usbmodem1411", 115200)
serial_interface2 = serialData.SerialInterface("/dev/tty.usbmodem1421", 115200)


for