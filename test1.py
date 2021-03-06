import serialData
import serial
import struct
import time
import os


serial_interface1 = serialData.SerialInterface("/dev/tty.usbmodem1411", 1000000)
serial_interface2 = serialData.SerialInterface("/dev/tty.usbmodem1421", 1000000)


try:
    while not serial_interface1.is_link_up() or not serial_interface2.is_link_up():
        time.sleep(0.1)
except KeyboardInterrupt:
    serial_interface1.stop_serial()
    exit()

print "pointed"
data = bytearray(os.urandom(12500))

print len(data)
print data


serial_interface1.send_data(data)
serial_interface2.send_data(data)


try:
    while serial_interface1.message_queue_is_empty() or serial_interface2.message_queue_is_empty():
        time.sleep(0.1)
except:
    serial_interface1.stop_serial()
    exit()

print data
a = serial_interface1.get_message()
print a
print "a"

b = serial_interface2.get_message()
print b
print "b"

print len(a)
print len(b)

counter = 0
for i, j in zip(a, data):
    if i != j:
        counter += 1
print counter

counter = 0
for i, j in zip(b, data):
    if i != j:
        counter += 1
print counter

counter = 0
for i, j in zip(a, b):
    if i != j:
        counter += 1
print counter

print bytearray(b) == data
print bytearray(a) == data


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
serial_interface2.stop_serial()