import os
import threading
import serialData
import time
from sys import stdout, exit
from os import name
import kbhit
from glob import glob

if name == 'nt':
    number = raw_input("Qual o numero da porta COM na qual o arduino esta conectado?")
    port = "COM" + str(number)
elif name == 'posix':
    port_list = []
    port_list += glob('/dev/tty.usbmodem*') + glob('/dev/ttyACM*') + glob('/dev/ttyUSB*')
    port = port_list[0]

baud_rate = 1000000

serial_interface = serialData.SerialInterface(port, baud_rate)

kb = kbhit.KBHit()

try:
    while not serial_interface.is_link_up():
        time.sleep(0.1)
except KeyboardInterrupt:
    serial_interface.stop_serial()
    exit()
    
try:
	while serial_interface.message_queue_is_empty() and not stop_program.is_set() and ((ans == 's') or (ans == 'S')):
	    time.sleep(0.01)

	msg = serial_interface.get_message()
	print msg

except KeyboardInterrupt:
        exit()
        