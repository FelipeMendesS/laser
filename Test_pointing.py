import serialData
import serial
import struct
import time
from os import name
from glob import glob
#
# if name == 'nt':
#     number = raw_input("Qual o numero da porta COM na qual o arduino esta conectado?")
#     port = "COM" + str(number)
# elif name == 'posix':
#     port_list = []
#     port_list += glob('/dev/tty.usbmodem*') + glob('/dev/ttyACM*') + glob('/dev/ttyUSB*')
#     port = port_list[0]

port = "/dev/tty.usbmodem1421"
# Max baud rate = 1000000
baud_rate = 1000000
# Voce precisa de um objeto serial_interface pra enviar dados. O metodo send_data nao eh estatico!!
serial_interface = serialData.SerialInterface(port, baud_rate)
try:
    while not serial_interface.is_link_up():
        time.sleep(0.1)
except KeyboardInterrupt:
    serial_interface.stop_serial()
    exit()

time.sleep(2)

print "Link is UP!"

serial_interface.stop_serial()