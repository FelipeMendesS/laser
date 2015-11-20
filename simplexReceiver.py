import os
import threading
import serialData
import time
from sys import stdout, exit
from os import name
import kbhit
from glob import glob

baud_rate = 1000000

serial_interface = serialData.SerialInterface("COM3", baud_rate)

try:
    while not serial_interface.is_link_up():
        time.sleep(0.1)
except KeyboardInterrupt:
    serial_interface.stop_serial()
    exit()

while 1:
	try:
		while serial_interface.message_queue_is_empty():
		    time.sleep(0.01)

		msg = serial_interface.get_message()
		stdout.write(str(msg))

	except KeyboardInterrupt:
		exit()

        