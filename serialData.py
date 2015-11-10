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

    #       --HEADER--
    #       \packet_length(2 bytes)\last_packet(1 byte)\actual_packet(1 byte)\
    #       --/HEADER--

    def send_data(self, file_to_send):
        max_packet_length = 12500
        if not file_to_send == '' and max_packet_length <= 0xffff:
            message_length = len(file_to_send)
            last_packet = int((message_length - 1)/max_packet_length) + 1
            #packet_begin = "01010101"
            #packet_end = "10011001"
            for actual_packet in range(1, last_packet + 1):
                packet = ""
                #packet = struct.pack('BB', packet_begin, packet_end)
                packet += str(struct.pack('BB', last_packet, actual_packet))
                pointer_packet_begin = (actual_packet - 1) * max_packet_length

                if (actual_packet != last_packet) or (message_length % max_packet_length == 0):
                    pointer_packet_end = pointer_packet_begin + max_packet_length
                else:
                    pointer_packet_end = pointer_packet_begin + message_length % max_packet_length

                packet_length = pointer_packet_end - pointer_packet_begin
                packet = str(struct.pack('H', packet_length)[::-1]) + packet
                packet += str(file_to_send[pointer_packet_begin : pointer_packet_end])

                #packet_ack = ""
                #packet += struct.pack('b', packet_ack))

                for x in xrange(0,len(packet)):
                    self.output_queue.put(packet[x], False)

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
        while not self.input_queue.empty():
            header_length = 4
            header = bytearray(header_length)
            for j in range(header_length):
                header[j] = struct.unpack('B', self.input_queue.get())[0]
            #interpretar o header...
            packet_length = header[0] * 256 + header[1]
            last_packet = header[2]
            actual_packet = header[3]

            packet = bytearray(packet_length)

            for j in range(packet_length):
                packet[j] = self.input_queue.get()
            #header é enviado com o packet?
            interpret_packets(self, header + packet):
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





