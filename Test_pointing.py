import serialData
import serial
import struct
import time
import os

port = "/dev/tty.usbmodem1411"
# Max baud rate = 1000000
baud_rate = 115200
# Voce precisa de um objeto serial_interface pra enviar dados. O metodo send_data nao eh estatico!!
serial_interface = serialData.SerialInterface(port, baud_rate)
try:
    while not serial_interface.is_link_up():
        time.sleep(0.1)
except KeyboardInterrupt:
    serial_interface.stop_serial()
    exit()

time.sleep(2)

serial_interface.stop_serial()