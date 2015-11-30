import serial
import threading
import time
import Queue
import struct
# import bitarray
import zfec
import numpy as np

# It seems to be reasonable for us to create differents initial bytes for the packets depending if we are requesting a
# retransmission or acknowledging the data being received or asking for a retransmission. Just as an example I'll start
# with some specific bit sequences:
# Data Packet: \x00\x55\xaa\xff
# Acknowledging: \x00\xaa\x55\xff
# Retransmit request: \xff\xaa\x55\xff
# Also, we are going to send acknowledgment packets for the first packet and the last packet only, so we know when the
# the message started to be received and when it was received completely. Probably logic in the interpret packets.
# Packet identifier:
# Composed by three bytes, first byte the message ID, and two other bytes are the packet sequence in the message!
#       --HEADER--
#       \packet_begin(4 bytes)\message_id(1 byte)\current_packet(2 bytes)\last_packet(2 bytes)\packet_length(2 bytes)\
#       --/HEADER--




class SerialInterface(object):

    DATA_PACKET_B = 0x0055aaff
    ACK_PACKET_B = 0x00aa55ff
    RETRANS_PACKET_B = 0xffaa5500
    MAX_PACKET_LENGTH = 64000
    HEADER_LENGTH = 11
    FIRST_POINTING_BYTE = 0x55
    LAST_POINTING_BYTE = 0xaa
    WINDOW_SIZE = 5
    # Timer for retransmission
    RETRANSMISSION_TIMER = 10
    PACKET_SENT = 0
    PACKET_RESENT = 1
    PACKET_ACKNOWLEDGED = 2

    def __init__(self, port, baud_rate):
        try:
            # Queues for
            self.input_queue = Queue.Queue()
            self.output_queue = Queue.Queue()
            self.retransmit_ack_queue = Queue.Queue()
            self.transmit_window_queue = Queue.Queue()
            self.message_queue = Queue.Queue()
            # Contains message being concatenated
            self.message = bytearray()
            self.baud_rate = baud_rate
            self.serial_port = serial.Serial(port, self.baud_rate, timeout=1, writeTimeout=1)
            #  Event to stop all threads and close serial port safely.
            self.stop_everything = threading.Event()
            self.is_it_pointed = threading.Event()
            self.received_first = threading.Event()
            self.packet_byte_array = bytearray()
            self.reading = threading.Thread(target=self.read_data)
            self.writing = threading.Thread(target=self.write_data)
            self.concatenating = threading.Thread(target=self.concatenate_received_bytes)
            self.current_packet = 0
            self.last_packet = 0
            self.reading.start()
            self.writing.start()
            self.concatenating.start()
            self.t = 0
            self.message_id = 0
            self.window_slots_left = 5
            self.data_to_send = bytearray()
            # Data structure with all the packets that were sent and didn't receive acknowledgement yet
            self.in_window_packets_dict = {}
            # Data structure with associated situation for each packet.
            self.packet_situation_dict = {}
            # List with all the retransmission timers being used
            self.retransmission_timers = 5*[(1, 0)]
        except serial.SerialException:
            if self.serial_port.isOpen():
                self.serial_port.close()
                self.stop_serial()
            else:
                self.stop_serial()
                raise

        # self.is_link_up = threading.Event()

    # Interface com o Abraco comeca
    def message_queue_is_empty(self):
        return self.message_queue.empty()

    def get_message(self):
        if not self.message_queue.empty():
            return self.message_queue.get()
        return '0'

    #       --HEADER--
    #       \packet_begin(4 bytes)\message_id(1 byte)\current_packet(2 bytes)\last_packet(2 bytes)\packet_length(2 bytes)\
    #       --/HEADER--

    def send_data(self, file_to_send):
        if not file_to_send == '':
            self.message_id += 1
            if self.message_id > 255:
                self.message_id = 1
            message_length = len(file_to_send)
            last_packet = int((message_length - 1)/self.MAX_PACKET_LENGTH) + 1
            for current_packet in range(1, last_packet + 1):
                pointer_packet_begin = (current_packet - 1) * self.MAX_PACKET_LENGTH
                if (current_packet != last_packet) or (message_length % self.MAX_PACKET_LENGTH == 0):
                    pointer_packet_end = pointer_packet_begin + self.MAX_PACKET_LENGTH
                else:
                    pointer_packet_end = pointer_packet_begin + message_length % self.MAX_PACKET_LENGTH
                packet_length = pointer_packet_end - pointer_packet_begin
                packet = bytearray(struct.pack('I', self.DATA_PACKET_B))
                packet += bytearray(struct.pack('B', self.message_id))
                packet += bytearray(struct.pack('HH', current_packet, last_packet))
                packet += bytearray(struct.pack('H', packet_length))
                packet += bytearray(SerialInterface.include_error_correction(file_to_send[pointer_packet_begin:pointer_packet_end]))
                self.output_queue.put(packet, False)

    @staticmethod
    def include_error_correction(packet):
        number_of_chunks = 100
        original_packet = packet[:]
        if len(original_packet) >= 10000:
            packet_list = SerialInterface.split_packet(original_packet, number_of_chunks)
            packet_encoder = zfec.Encoder(number_of_chunks, 107)
            packet_list = packet_encoder.encode(packet_list)
            for i in range(len(packet_list)):
                packet_list[i] += bytearray(struct.pack('I', np.frombuffer(packet_list[i], 'uint8').sum()))
            final_packet = bytearray()
            for chunk in packet_list:
                final_packet += chunk
            return final_packet
        else:
            return original_packet + bytearray(struct.pack('I', np.frombuffer(original_packet, 'uint8').sum()))

    @staticmethod
    def split_packet(packet, number_of_parts):
        if len(packet) % 100 != 0:
            packet += bytearray(100 - (len(packet) % 100))
        division = len(packet) / number_of_parts
        return [packet[division * i: division * (i + 1)] for i in xrange(number_of_parts)]

    @staticmethod
    def real_packet_length(packet_length):
        if packet_length < 10000:
            return packet_length + 4
        else:
            if packet_length % 100 == 0:
                return packet_length * 107 / 100 + 4 * 107
            else:
                return (packet_length / 100 + 1) * 107 + 4 * 107

    def total_number_of_packets(self):
        return self.last_packet

    def current_processed_packet(self):
        if self.current_packet == 0 and self.last_packet != 0:
            return self.last_packet
        else:
            return self.current_packet

    # Interface com o abraco termina

    def check_retransmission_timer(self, packet_identifier, index):
        self.retransmission_timers[index][0] = 1
        identifier = struct.unpack('I', packet_identifier + bytearray(1))[0]
        if self.packet_situation_dict[identifier] != self.PACKET_ACKNOWLEDGED:
            packet = self.in_window_packets_dict[identifier]
            packet_identifier = packet[4:7]
            self.transmit_window_queue.put(packet, block=False)
            self.transmit_window_queue.put(packet_identifier, block=False)
            self.packet_situation_dict[identifier] = self.PACKET_RESENT
        else:
            self.packet_situation_dict.pop(identifier)
            self.in_window_packets_dict.pop(identifier)

    def transmission_manager(self):
        index = 0
        while not self.is_it_pointed.is_set():
            time.sleep(0.1)
            continue
        while not self.stop_everything.is_set():
            if not self.retransmit_ack_queue.empty() and len(self.data_to_send) < 1000:
                self.data_to_send.extend(self.retransmit_ack_queue.get(block=False))
            elif not self.transmit_window_queue.empty() and len(self.data_to_send) < 1000:
                data = self.transmit_window_queue.get(block=False)
                if len(data) == 3:
                    self.packet_situation_dict[struct.unpack('I', data + bytearray(1))[0]] = self.PACKET_SENT
                    timer = threading.Timer(self.RETRANSMISSION_TIMER, self.check_retransmission_timer,
                                            args=(struct.unpack('I', data + bytearray(1))[0], index))
                    if self.retransmission_timers[index][0] == 1:
                        self.retransmission_timers[index] = (0, timer)
                        timer.start()
                        index += 1
                        if index == 5:
                            index = 0
                # logic here that indicates that a packet was sent but is waiting for confirmation
                # also, start timer fo rthis packet retransmission
                # see : https://docs.python.org/2/library/threading.html#timer-objects
                self.data_to_send.extend(self.transmit_window_queue.get(block=False))
            while self.window_slots_left > 0 and not self.output_queue.empty():
                packet = self.output_queue.get(block=False)
                packet_identifier = packet[4:7]
                self.transmit_window_queue.put(packet, block=False)
                self.transmit_window_queue.put(packet_identifier, block=False)
                # Added packet to dictionary
                self.in_window_packets_dict[struct.unpack('I', packet_identifier + bytearray(1))[0]] = packet
                # When acknowledge is received, this is incremented (by the interpret packets)
                self.window_slots_left -= 1

    def wait_for_data(self, minimum_buffer_size, sleep_time):
        counter = 0
        while self.serial_port.inWaiting() < minimum_buffer_size and not self.stop_everything.is_set():
            time.sleep(sleep_time)
            counter += 1
            if counter >= 2 and self.serial_port.inWaiting() >= 1:
                break
        return

    def read_data(self):
        time.sleep(2)
        self.serial_port.flushInput()
        index = -1
        byte_to_check = self.FIRST_POINTING_BYTE
        pointing_data = bytearray()
        pointing_data.extend(self.serial_port.read((self.serial_port.inWaiting())))
        while not self.is_it_pointed.is_set():
            self.wait_for_data(1, 0.001)
            if self.stop_everything.is_set():
                break
            pointing_data.extend(self.serial_port.read((self.serial_port.inWaiting())))
            for j, data in enumerate(pointing_data):
                if data == byte_to_check and not self.received_first.is_set():
                    self.received_first.set()
                    byte_to_check = self.LAST_POINTING_BYTE
                    index = j
                    break
                if data == byte_to_check and self.received_first.is_set():
                    self.is_it_pointed.set()
            if not self.received_first.is_set():
                pointing_data = bytearray()
            elif not self.is_it_pointed.is_set() and index != -1:
                pointing_data = pointing_data[index:]
                index = -1
            elif not self.is_it_pointed.is_set():
                pointing_data = bytearray()

        self.input_queue.put(pointing_data)
        # packet_detected = False
        # while self.serial_port.inWaiting() < 1 and not self.stop_everything.is_set():
        #     try:
        #         initial_data += self.serial_port.readline()
        #         # for i in range(len(initial_data) - 3):
        #         #     if struct.unpack('I', initial_data[i:i+4])[0] == self.DATA_PACKET_B:
        #         #         initial_data = initial_data[i:]
        #         #         packet_detected = True
        #         #         break
        #         # if not packet_detected and len(initial_data) >= 4:
        #         #     initial_data = initial_data[len(initial_data)-3:]
        #     except serial.SerialException:
        #         if self.serial_port.isOpen():
        #             self.serial_port.close()
        #             self.stop_serial()
        #         else:
        #             raise
        #     time.sleep(0.001)
        # self.input_queue.put(initial_data, False)
        # # read data from serial port continuously
        while not self.stop_everything.is_set():
            self.wait_for_data(100, 0.001)
            if self.stop_everything.is_set():
                break
            self.input_queue.put(self.serial_port.read(self.serial_port.inWaiting()), False)

        self.writing.join()
        self.concatenating.join()
        if self.serial_port.isOpen():
            self.serial_port.close()

    # The basic idea is to send an amount of data that is less than the maximum the port can transmit per second
    # I currently don't know how to reliably check how many bytes I have in the output buffer of the computer
    # at any given time, so I will use a simple calculation to decide how many bytes I send for each millisecond so
    # I never completely fill the output buffer. It's obviously not 100% efficient.
    def write_data(self):
        # We need to urgently change this structure with an almost empty write data for more efficient writing
        # In this case the write data thread would be completely empty of any processing except writing data to
        # the serial port!!! And we would need another thread to deal with the processing.
        time.sleep(2)
        byte_rate = self.baud_rate/10000
        number_of_bytes_sent = byte_rate
        self.serial_port.flushOutput()

        while not self.is_it_pointed.is_set() and not self.stop_everything.is_set():
            if not self.received_first.is_set():
                self.serial_port.write(bytearray(struct.pack('B', self.FIRST_POINTING_BYTE)))
                self.serial_port.write(bytearray(struct.pack('B', self.LAST_POINTING_BYTE)))
                time.sleep(0.1)
            else:
                self.serial_port.write(bytearray(struct.pack('B', self.FIRST_POINTING_BYTE)))
                self.serial_port.write(bytearray(struct.pack('B', self.LAST_POINTING_BYTE)))
                time.sleep(0.1)

        time.sleep(0.5)
        self.serial_port.write(bytearray(struct.pack('B', self.FIRST_POINTING_BYTE)))
        self.serial_port.write(bytearray(struct.pack('B', self.LAST_POINTING_BYTE)))
        self.serial_port.write(bytearray(struct.pack('B', self.FIRST_POINTING_BYTE)))
        self.serial_port.write(bytearray(struct.pack('B', self.LAST_POINTING_BYTE)))
        self.serial_port.write(bytearray(struct.pack('B', self.FIRST_POINTING_BYTE)))
        self.serial_port.write(bytearray(struct.pack('B', self.LAST_POINTING_BYTE)))
        time.sleep(0.5)
        self.serial_port.write(bytearray(struct.pack('B', self.FIRST_POINTING_BYTE)))
        self.serial_port.write(bytearray(struct.pack('B', self.LAST_POINTING_BYTE)))
        self.serial_port.write(bytearray(struct.pack('B', self.FIRST_POINTING_BYTE)))
        self.serial_port.write(bytearray(struct.pack('B', self.LAST_POINTING_BYTE)))
        self.serial_port.write(bytearray(struct.pack('B', self.FIRST_POINTING_BYTE)))
        self.serial_port.write(bytearray(struct.pack('B', self.LAST_POINTING_BYTE)))

        sent = False
        while not self.stop_everything.is_set() or (self.stop_everything.is_set() and len(self.data_to_send) > 0):
            if len(self.data_to_send) < byte_rate:
                number_of_bytes_sent = len(self.data_to_send)
            try:
                if self.serial_port.outWaiting() < 2 * byte_rate:
                    self.serial_port.write(self.data_to_send[:number_of_bytes_sent])
                sent = True
            except serial.SerialException:
                if not self.serial_port.isOpen():
                    self.stop_serial()
                else:
                    raise
            if sent:
                self.data_to_send = self.data_to_send[number_of_bytes_sent:]
                sent = False
            number_of_bytes_sent = byte_rate
            time.sleep(0.0001)

        # while not self.stop_everything.is_set() or\
        #         (self.stop_everything.is_set and (not self.output_queue.empty() or len(self.data_to_send) > 0)):
        #     time.sleep(0.001)
        #     if not self.retransmit_ack_queue.empty() and len(self.data_to_send) < 1000:
        #         self.data_to_send.extend(self.retransmit_ack_queue.get(block=False))
        #     elif not self.transmit_window_queue.empty() and len(self.data_to_send) < 1000:
        #         if
        #         self.data_to_send.extend(self.transmit_window_queue.get(block=False))
        #     if len(self.data_to_send) < byte_rate:
        #         number_of_bytes_sent = len(self.data_to_send)
        #     try:
        #         if len(self.data_to_send) > 0:
        #             self.serial_port.write(self.data_to_send[:number_of_bytes_sent])
        #     except serial.SerialException:
        #         if not self.serial_port.isOpen():
        #             self.stop_serial()
        #         else:
        #             raise
        #     data_to_send = self.data_to_send[number_of_bytes_sent:]
        #     number_of_bytes_sent = byte_rate

    def stop_serial(self):
        if not self.stop_everything.is_set():
            self.stop_everything.set()

    # Funcao que junta os bytes recebidos, que estao na input queue, e quando ela detecta um pacote
    # inteiro, manda pro interpret_packets.
    def concatenate_received_bytes(self):
        received_bytes = bytearray()
        found_packet = False
        packet_type = ""
        # debug variables (delete later)
        packet_length = 0
        total_packet_length = 0
        index = 0
        while not self.stop_everything.is_set():
            if not self.input_queue.empty():
                received_bytes.extend(self.input_queue.get(block=False))
                index = 0
            if not found_packet and index != -1:
                index, packet_type = self.find_beginning_of_packet(received_bytes)
                if index != -1:
                    found_packet = True
                    received_bytes = received_bytes[index:]
            if len(received_bytes) >= self.HEADER_LENGTH and packet_length == 0 and found_packet:
                packet_length = struct.unpack('H', received_bytes[self.HEADER_LENGTH-4:self.HEADER_LENGTH-2])[0]
                total_packet_length = SerialInterface.real_packet_length(packet_length)
            elif len(received_bytes) >= (self.HEADER_LENGTH + total_packet_length) and found_packet:
                self.interpret_packets(received_bytes[:total_packet_length + self.HEADER_LENGTH], packet_length, packet_type)
                received_bytes = received_bytes[total_packet_length + self.HEADER_LENGTH:]
                packet_length = 0
                found_packet = False
            if self.input_queue.qsize() < 100:
                time.sleep(0.05)
            # current_length = len(received_bytes)

    # Add option for different types of packets
    def find_beginning_of_packet(self, byte_array):
        for i in range(len(byte_array) - 3):
            a = struct.unpack('I', byte_array[i:i+4])[0]
            if a == self.DATA_PACKET_B:
                return (i, "data")
            elif a == self.ACK_PACKET_B:
                return (i, "acknowledge")
            elif a == self.RETRANS_PACKET_B:
                return (i, "retransmission")
        return -1
    # If the packet is corrupted in an irreversible way this function
    # just returns 0. Otherwise it returns the original packet.
    @staticmethod
    def recover_original_packet(packet, packet_size):
        if packet_size < 10000:
            if struct.unpack('I', packet[-4:])[0] != np.frombuffer(packet[:-4], 'uint8').sum():
                return 0
            return packet[:-4]
        packet_list = SerialInterface.split_packet(packet, 107)
        correct_packet_list = []
        list_of_correct_chunks = []
        for i, chunk in enumerate(packet_list):
            checksum = struct.unpack('I', chunk[-4:])[0]
            if checksum == np.frombuffer(chunk[:-4], 'uint8').sum():
                list_of_correct_chunks.append(chunk[:-4])
                correct_packet_list.append(i)
                if len(correct_packet_list) == 100:
                    break
            else:
                print "found error"
        if len(correct_packet_list) != 100:
            return 0
        decoder = zfec.Decoder(100, 107)
        decoded_packet = bytearray()
        decoded_chunks = decoder.decode(list_of_correct_chunks, correct_packet_list)
        for chunk in decoded_chunks:
            decoded_packet += chunk
        return decoded_packet[:packet_size]

    # Funcao que checa o pacote, contra erros por exemplo, e se ele eh parte de uma mensagem maior, junta esse pacote.
    # Se detecta que pacote foi perdido, chama o request_retransmission. Quando a mensagem esta completa adiciona
    # a fila de mensagens.
    def interpret_packets(self, byte_array, packet_length, packet_type):
        if packet_type == "data"
            packet_decoded = SerialInterface.recover_original_packet(byte_array[self.HEADER_LENGTH:], packet_length)
            if packet_decoded == 0:
                print "error"
                return
            if len(self.message) == 0:
                self.t = time.clock()
            self.message += packet_decoded
            self.last_packet, self.current_packet = struct.unpack('BB', byte_array[self.HEADER_LENGTH-2:self.HEADER_LENGTH])
            print self.last_packet, self.current_packet
            print self.output_queue.qsize()
            if self.current_packet == self.last_packet:
                self.current_packet = 0
                self.message_queue.put(self.message)
                print time.clock() - self.t
                self.message = bytearray()
        elif packet_type == "acknowledge"
            self.window_slots_left += 1
        elif packet_type == "retransmission"
            
    def is_link_up(self):
        return self.is_it_pointed.is_set()

    def simplex_mode(self):
        time.sleep(2)
        self.is_it_pointed.set()

    # Manda uma mensagem (formato a definir) pra pedir um pacote que seja retransmitido pelo outro lado da conexao.
    # Eh importante que definamos alguma forma de identificar as mensagens unicamente, por exemplo com uma ID no header,
    # assim podemos identificar para o transmissor o ID da mensagem e pacote que deve ser retransmitido.
    # Alem disso, parece razoavel avisar o transmissor pelo menos que o primeiro e o ultimo pacote foram recebiudos com
    # sucesso.
    def request_retransmission(self, packet_number, message_id):
        # request_byte = bytearray(bitarray.bitarray('10101010').tobytes())
        packet = request_byte + bytearray(struct.pack('BB', packet_number, message_id))
        self.output_queue.put(packet)

    # Chamado pelo interpret_packets quando ele detecta que foi pedida uma retransmissao. Para isso ocorrer precisamos
    # mante jum buffer dos pacotes enviados ate o momento que eles recebem acknowledgement de que foram recebidos
    # completamente.
    def resend_packet(self, packet_number):
        return

    def send_acknowledgement(self, packet_number):
        return
