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

print "Starting text reception"

current_line = ''

try:
    while 1:
        while serial_interface.message_queue_is_empty():
            time.sleep(0.01)

        msg = serial_interface.get_message()
        if msg[0] != 10 and msg[0] != 8:
            current_line += chr(msg[0])
        elif msg[0] != 8:
            current_line = ''
        if msg[0] != 8 or len(current_line) == 0:
            stdout.write(msg)
            stdout.flush()
        else:
            current_line = current_line[:len(current_line)-1]
            stdout.write('\r')
            for character in current_line:
                stdout.write(character)
            stdout.flush()
        if msg[0] == 27:
            serial_interface.stop_serial()
            exit()

except KeyboardInterrupt:
    serial_interface.stop_serial()
    exit()