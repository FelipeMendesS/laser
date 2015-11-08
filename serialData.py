import serial
# import matplotlib.pyplot as plt
# import numpy as np
import threading
import time
import Queue


class SerialInterface(object):

    def __init__(self, port, baud_rate):
        self.input_queue = Queue.Queue()
        self.output_queue = Queue.Queue()
        self.message_queue = Queue.Queue()
        self.baud_rate = baud_rate
        self.serial_port = serial.Serial(port, baud_rate, timeout=0, writeTimeout=0)
        self.stop_everything = threading.Event()

        self.reading = threading.Thread(target=self.read_data, args=self)
        self.writing = threading.Thread(target=self.write_data, args=self)
        self.joining = threading.Thread(target=self.join_packet, args=self)

        self.reading.start()
        self.writing.start()
        self.joining.start()

        # self.is_link_up = threading.Event()

    def message_queue_is_empty(self):
        return self.message_queue.empty()

    def message_get(self):
        if not self.message_queue.empty():
            return self.message_queue.get()
        return 0

    def send_data(self, byte_array):
        self.output_queue.put(byte_array, block=False)

    def wait_for_data(self, minimum_buffer_size, sleep_time):
        while self.serial_port.inWaiting() < minimum_buffer_size:
            time.sleep(sleep_time)
        return

    def read_data(self):
        self.serial_port.flushInput()
        while self.serial_port.inWaiting() < 200:
            self.serial_port.readline()
            time.sleep(0.1)
            print self.serial_port.inWaiting()
        # read data from serial port continuously
        while not self.stop_everything.is_set():
            self.wait_for_data(200, 0.01)
            self.input_queue.put(self.serial_port.read(self.serial_port.inWaiting()), False)
        self.writing.join()
        self.serial_port.close()


    def write_data(self):
        data_to_send = b""
        self.serial_port.flushOutput()
        for i in 
        while not self.stop_everything.is_set():
            if self.output_queue.empty() or self.serial_port.outWaiting() > 100:
                time.sleep(0.001)
            else:
                data_to_send = self.output_queue.get(block=False)
                self.serial_port.write(byte_array)

    def join_packet(self):
        parts_list = []
        while not self.stop_everything.is_set():
            if self.input_queue.empty():
                time.sleep(0.01)
            else:
                parts_list.append(self.input_queue.get())
                length = 0
                for item in parts_list:
                    length += len(item)
                if length >= 10000:
                    all_data = b"".join(parts_list)
                    self.message_queue.put(all_data[:10000], block=False)
                    parts_list = [all_data[10000:]]

    def stop_serial(self):
        self.stop_everything.set()



