import serialData
import serial
import struct
import time
import os
import glob

test_array = bytearray(os.urandom(100))


if os.name == 'nt':
    number = raw_input("Qual o numero da porta COM na qual o arduino esta conectado?")
    port = "COM" + str(number)
elif os.name == 'posix':
    port_list = []
    port_list += glob('/dev/tty.usbmodem*') + glob('/dev/ttyACM*') + glob('/dev/ttyUSB*')
    port = port_list[0]

serial_interface1 = serialData.SerialInterface(port, 1000000)

try:
    while not serial_interface1.is_link_up():
        time.sleep(0.1)
except KeyboardInterrupt:
    serial_interface1.stop_serial()
    exit()

data = bytearray("Felipe") + bytearray(struct.pack('B', 48))*50000

# print len(data)
# print data
serial_interface1.send_data(data)
# serial_interface2.send_data(data)

serial_interface1.send_data(data)
# serial_interface2.send_data(data)
#
# serial_interface1.send_data(test_array)
# serial_interface2.send_data(test_array)

try:
    # while serial_interface1.message_queue_is_empty() or serial_interface2.message_queue_is_empty():
    while serial_interface1.message_queue_is_empty():
        # print serial_interface1.message_queue_is_empty()
        # print serial_interface2.message_queue_is_empty()
        time.sleep(0.1)
except:
    print "oi"
    serial_interface1.stop_serial()
    exit()
    # if serial_interface2.serial_port.isOpen():
    #     serial_interface2.serial_port.close()

# print data
a = serial_interface1.get_message()
# print a

serial_interface1.send_data(a)
serial_interface1.send_data(a)


while serial_interface1.message_queue_is_empty():
    time.sleep(0.1)

b = serial_interface1.get_message()



counter = 0
for i, j in zip(a, b):
    if i != j:
        counter += 1
# print counter

if counter == 0:
    print "xinarow"
    while serial_interface1.message_queue_is_empty():
        time.sleep(0.1)
    b = serial_interface1.get_message()
    # print b

# b = serial_interface2.get_message()
# print b

counter = 0
for i, j in zip(b, data):
    if i != j:
        counter += 1
# print counter

counter = 0
for i, j in zip(a, data):
    if i != j:
        counter += 1
# print counter


print bytearray(b) == data

# try:
#     while serial_interface1.message_queue_is_empty() or serial_interface2.message_queue_is_empty():
#         # print serial_interface1.message_queue_is_empty()
#         # print serial_interface2.message_queue_is_empty()
#         time.sleep(0.1)
# except:
#     if serial_interface1.serial_port.isOpen():
#         serial_interface1.serial_port.close()
#     if serial_interface2.serial_port.isOpen():
#         serial_interface2.serial_port.close()
#
# print test_array
# a = serial_interface1.get_message()
# b = serial_interface2.get_message()
# print bytearray(a) == test_array
# print bytearray(b) == test_array

serial_interface1.stop_serial()
# serial_interface2.stop_serial()
