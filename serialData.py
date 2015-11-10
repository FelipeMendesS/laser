import serial
# import matplotlib.pyplot as plt
# import numpy as np
import threading
import time
import Queue
import struct


class SerialInterface(object):

    def __init__(self, port, baud_rate):
        self.input_queue = Queue.Queue()
        self.output_queue = Queue.Queue()
        self.message_queue = Queue.Queue()
        self.baud_rate = baud_rate
        self.serial_port = serial.Serial(port, baud_rate, timeout=0, writeTimeout=0)
        self.stop_everything = threading.Event()
        self.packet_byte_array = bytearray()

        self.reading = threading.Thread(target=self.read_data, args=self)
        self.writing = threading.Thread(target=self.write_data, args=self)
        self.joining = threading.Thread(target=self.join_packet, args=self)

        self.reading.start()
        self.writing.start()
        self.joining.start()

        # self.is_link_up = threading.Event()

    # Interface com o Abraco começa
    def message_queue_is_empty(self):
        return self.message_queue.empty()

    def get_message(self):
        if not self.message_queue.empty():
            return self.message_queue.get()
        return 0

    def input_queue_is_empty(self):
        return self.input_queue.empty()

    def input_get(self):
        if not self.input_queue.empty():
            return self.input_queue.get()
        return 0

    def input_put(data):
        self.input_queue.put(data):

    def output_queue_is_empty(self):
        return self.output_queue.empty()

    def output_get(self):
        if not self.output_put.empty():
            return self.output_queue.get()
        return 0

    def output_put(data):
        self.output_queue.put(data)

    #   /package_length(2 bytes)/last_package(1 byte)/actual_package(1 byte)/package

    def send_data(self, file_to_send):
        max_package_length = 12500
        message_byte = file_to_send
        message_length = len(message_byte)
        package_max = int((message_length - 1)/max_package_length) + 1
        #package_begin = "01010101"
        #package_end = "10011001"

        for j in range(1, package_max + 1):
            package = ""
            #package = str(struct.pack('BB', package_begin, package_end))
            package += str(struct.pack('BB', package_max, j))

            if j != package_max:
                package = str(struct.pack('BB', max_package_length/256, max_package_length % 256)) + package
                package += str(message_byte[(j-1)*max_package_length:j*max_package_length])
            else:
                if message_length == max_package_length:
                    package = str(struct.pack('BB', message_length / 256, message_length % 256)) + package
                    package += str(message_byte[(j-1)*max_package_length:(j-1)*max_package_length + max_package_length + 1])
                else:
                    package = str(struct.pack('BB', (message_length % max_package_length)/256, (message_length % max_package_length) % 256)) + package
                    package += str(message_byte[(j-1)*max_package_length:(j-1)*max_package_length + message_length % max_package_length + 1])

            #package_ack = ""
            #package += str(struct.pack('b', package_ack))

            self.output_queue.put(package, False)

    # Interface com o abraco termina

    def wait_for_data(self, minimum_buffer_size, sleep_time):sme
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

    # Funcao que junta os bytes recebidos, que estao na input queue, e quando ela detecta um pacote
    # inteiro, manda pro interpret_packets.
    def concatenate_received_bytes(self, bytearray):
        return

    #Funcao que checa o pacote, contra erros por exemplo, e se ele eh parte de uma mensagem maior, junta esse pacote.
    # Se detecta que pacote foi perdido, chama o request_retransmission. Quando a mensagem esta completa adiciona
    # a fila de mensagens.
    def interpret_packets(self, bytearray):
        return

    # Manda uma mensagem (formato a definir) pra pedir um pacote que seja retransmitido pelo outro lado da conexao.
    # Eh importante que definamos alguma forma de identificar as mensagens unicamente, por exemplo com uma ID no header,
    # assim podemos identificar para o transmissor o ID da mensagem e pacote que deve ser retransmitido.
    # Alem disso, parece razoavel avisar o transmissor pelo menos que o primeiro e o ultimo pacote foram recebiudos com sucesso.
    def request_retransmission(self):
        return

    # Chamado pelo interpret_packets quando ele detecta que foi pedida uma retransmissao. Para isso ocorrer precisamos manter
    # jum buffer dos pacotes enviados ate o momento que eles recebem acknowledgement de que foram recebidos completamente.
    def resend_packet(self):
        return

    # :P





