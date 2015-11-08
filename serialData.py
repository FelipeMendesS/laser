import serial
import matplotlib.pyplot as plt
# import numpy as np
import threading
import time
import Queue


def is_float(s):
    try:
        number = float(s)
        return number
    except:
        return 0


def wait_for_data(serial_port, )

def read_data(serial_port, data_queue, end_measurement_event):
    is_pointed = False
    serial_port.flushInput()
    while serial_port.inWaiting() < 200:
        serial_port.readline()
        time.sleep(0.1)
        print serial_port.inWaiting()
    # Pointing
    while not is_pointed:

    while not end_measurement_event.is_set():
        if serial_port.inWaiting() < 200:
            time.sleep(0.1)
            print serial_port.inWaiting()
            continue
        data_queue.put(serial_port.read(serial_port.inWaiting()), False)
    return


def store_data(data_matrix, data_queue, end_measurement_event):
    data_string = ""
    for j in range(10):
        data_matrix.append([])
    for i in range(5):
        while data_queue.qsize() < 3 and len(data_string) < 400:
            time.sleep(0.1)
        while not data_queue.empty():
            data_string += data_queue.get(False)
        data_string = data_string.split("mamai\r\n")[-1]

    for i in range(1000):
        while data_queue.qsize() < 3 and len(data_string) < 400:
            time.sleep(0.1)
        while not data_queue.empty():
            data_string += data_queue.get(False)
        list_of_data = data_string.split("\r\n", 11)
        for j, data in enumerate(list_of_data):
            if j >= 0 and j < 10:
                data_matrix[j].append(is_float(data))
            if j == 11:
                data_string = data
    end_measurement_event.set()


ser = serial.Serial('/dev/cu.usbmodem1411', 9600, timeout=2)

end_measurement = threading.Event()
data_queue = Queue.Queue()
data_matrix = []

reading = threading.Thread(target=read_data, args=(ser, data_queue,
                           end_measurement))

storing = threading.Thread(target=store_data, args=(data_matrix,
                           data_queue, end_measurement))

reading.start()
storing.start()

reading.join()
ser.close()

for i in range(10):
    plt.plot(data_matrix[i], 'bs-')
    print data_matrix[i][::5]
    print len(data_matrix[i])
plt.show()
