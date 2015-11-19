import serialData
import serial
import struct
import time
import os

port = "COM32"
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