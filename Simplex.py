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

time.sleep(2)
serial_interface.simplex_mode()

try:
    while not serial_interface.is_link_up():
        time.sleep(0.1)

except KeyboardInterrupt:
    serial_interface.stop_serial()
    exit()

print "Link connected. Press ESC to close your program and the receiver"

c = ''
b = bytearray()
current_line = ''

try:
    while 1:
        if kb.kbhit():
            c = kb.getch()
            b.append(ord(c))
            if ord(c) != 10 and ord(c) != 127:
                current_line += c
            elif ord(c) != 127:
                current_line = ''
            if ord(c) != 127 or len(current_line) == 0:
                stdout.write(c)
                stdout.flush()
            elif ord(c) == 127:
                stdout.write('\r')
                for i in range(len(current_line)):
                    stdout.write(' ')
                stdout.write('\r')
                current_line = current_line[:len(current_line)-1]
                for character in current_line:
                    stdout.write(character)
                stdout.flush()
            serial_interface.send_data(bytearray([ord(c)]))
            if ord(c) == 27:
                print ""
                serial_interface.stop_serial()
                exit()

except KeyboardInterrupt:
    serial_interface.stop_serial()
    exit()
