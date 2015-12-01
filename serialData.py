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
    MAX_PACKET_LENGTH = 25000
    HEADER_LENGTH = 11
    ACK_RETRANS_HEADER_LENGTH = 7
    FIRST_POINTING_BYTE = 0x55
    LAST_POINTING_BYTE = 0xaa
    WINDOW_SIZE = 5
    # Timer for retransmission
    RETRANSMISSION_TIMER = 5
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
            self.manager = threading.Thread(target=self.transmission_manager)
            self.reading.start()
            self.writing.start()
            self.concatenating.start()
            self.manager.start()
            self.t = 0
            self.message_id = 0
            self.window_slots_left = 5
            self.data_to_send = bytearray()
            # Data structure with all the packets that were sent and didn't receive acknowledgement yet
            self.in_window_packets_dict = {}
            # Data structure with associated situation for each packet.
            self.packet_timer_dict = {}
            # dictionary with all messages received
            self.message_dict = {}
            self.received_packet_status = {}
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

    # Interface com o abraco termina
    def check_retransmission_timer(self, packet_identifier):
        self.packet_timer_dict[packet_identifier] = (1, 0)
        packet = self.in_window_packets_dict[packet_identifier]
        byte_packet_identifier = packet[4:7]
        self.transmit_window_queue.put(packet, block=False)
        self.transmit_window_queue.put(byte_packet_identifier, block=False)
        print "resending"

    def transmission_manager(self):
        while not self.is_it_pointed.is_set():
            time.sleep(0.1)
            continue
        while not self.stop_everything.is_set():
            if not self.retransmit_ack_queue.empty() and len(self.data_to_send) < 1000:
                data = self.retransmit_ack_queue.get(block=False)
                if len(data) == 3:
                    packet_identifier = struct.unpack('I', data + bytearray(1))[0]
                    timer = threading.Timer(self.RETRANSMISSION_TIMER, self.check_retransmission_timer,
                                            args=(struct.unpack('I', data + bytearray(1))[0],))
                    if self.packet_timer_dict.has_key(packet_identifier) and self.packet_timer_dict[packet_identifier][0] == 0:
                        self.packet_timer_dict[packet_identifier][1].cancel()
                    self.packet_timer_dict[packet_identifier] = (0, timer)
                    timer.start()
                # logic here that indicates that a packet was sent but is waiting for confirmation
                # also, start timer fo this packet retransmission
                # see : https://docs.python.org/2/library/threading.html#timer-objects
                else:
                    self.data_to_send.extend(data)
                # print "sending ack or ret"
            elif not self.transmit_window_queue.empty() and len(self.data_to_send) < 1000:
                data = self.transmit_window_queue.get(block=False)
                if len(data) == 3:
                    packet_identifier = struct.unpack('I', data + bytearray(1))[0]
                    timer = threading.Timer(self.RETRANSMISSION_TIMER, self.check_retransmission_timer,
                                            args=(struct.unpack('I', data + bytearray(1))[0],))
                    if self.packet_timer_dict.has_key(packet_identifier) and self.packet_timer_dict[packet_identifier][0] == 0:
                        self.packet_timer_dict[packet_identifier][1].cancel()
                    self.packet_timer_dict[packet_identifier] = (0, timer)
                    timer.start()
                # logic here that indicates that a packet was sent but is waiting for confirmation
                # also, start timer fo this packet retransmission
                # see : https://docs.python.org/2/library/threading.html#timer-objects
                else:
                    self.data_to_send.extend(data)
                    # print "sending normal data"
            while self.window_slots_left > 0 and not self.output_queue.empty():
                packet = self.output_queue.get(block=False)
                packet_identifier = packet[4:7]
                self.transmit_window_queue.put(packet, block=False)
                self.transmit_window_queue.put(packet_identifier, block=False)
                # Added packet to dictionary
                self.in_window_packets_dict[struct.unpack('I', packet_identifier + bytearray(1))[0]] = packet
                # When acknowledge is received, this is incremented (by the interpret packets)
                self.window_slots_left -= 1
            time.sleep(0.001)

    def wait_for_data(self, minimum_buffer_size, sleep_time):
        counter = 0
        while self.serial_port.inWaiting() < minimum_buffer_size and not self.stop_everything.is_set():
            time.sleep(sleep_time)
            counter += 1
            # if counter % 1000 == 0:
            #     # print "Waiting Bytes"
            #     # print self.serial_port.inWaiting()
            if counter >= 2 and self.serial_port.inWaiting() >= 1:
            #     # print "getting Bytes"
            #     # print self.serial_port.inWaiting()
                break

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
        byte_rate = 2*self.baud_rate/10000
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
                # if len(self.data_to_send) > 0:
                    # print "sending"
                    # print self.data_to_send
                # if number_of_bytes_sent > 0:
                #     # print "bytes to send"
                #     # print number_of_bytes_sent
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
            time.sleep(0.01)

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
        packet_number = 0
        packet_length = 0
        message_id = 0
        total_packet_length = 0
        index = 0
        while not self.stop_everything.is_set():
            if not self.input_queue.empty():
                received_bytes.extend(self.input_queue.get(block=False))
                # print"received"
                # print received_bytes
                index = 0
            if not found_packet and index != -1:
                index, packet_type = self.find_beginning_of_packet(received_bytes)
                if index != -1:
                    found_packet = True
                    received_bytes = received_bytes[index:]
                if len(received_bytes) >= 3 and not found_packet:
                    received_bytes = received_bytes[-3:]
            if packet_type == "data":
                if len(received_bytes) >= self.HEADER_LENGTH and packet_length == 0 and found_packet:
                    packet_length = struct.unpack('H', received_bytes[self.HEADER_LENGTH-2:self.HEADER_LENGTH])[0]
                    packet_identifier = struct.unpack('I', received_bytes[4:7] + bytearray(1))[0]
                    total_packet_length = SerialInterface.real_packet_length(packet_length)
                elif len(received_bytes) >= (self.HEADER_LENGTH + total_packet_length) and found_packet:
                    self.interpret_packets(received_bytes[:total_packet_length + self.HEADER_LENGTH], packet_length, packet_type, packet_identifier)
                    received_bytes = received_bytes[total_packet_length + self.HEADER_LENGTH:]
                    packet_length = 0
                    packet_type = ""
                    found_packet = False
            elif packet_type == "acknowledge" or packet_type == "retransmission":
                if len(received_bytes) >= self.ACK_RETRANS_HEADER_LENGTH and found_packet:
                    packet_identifier = struct.unpack('I', received_bytes[4:self.ACK_RETRANS_HEADER_LENGTH] + bytearray(1))[0]
                    self.interpret_packets(received_bytes[4:self.ACK_RETRANS_HEADER_LENGTH], 3, packet_type, packet_identifier)
                    packet_type = ""
                    found_packet = False
                    received_bytes = received_bytes[self.ACK_RETRANS_HEADER_LENGTH:]
            # if self.input_queue.qsize() < 100:
                # time.sleep(0.05)
            # current_length = len(received_bytes)

    # Add option for different types of packets
    def find_beginning_of_packet(self, byte_array):
        for i in range(len(byte_array) - 3):
            a = struct.unpack('I', byte_array[i:i+4])[0]
            if a == self.DATA_PACKET_B:
                return i, "data"
            elif a == self.ACK_PACKET_B:
                return i, "acknowledge"
            elif a == self.RETRANS_PACKET_B:
                return i, "retransmission"
        return -1, "nada"
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
    def interpret_packets(self, byte_array, packet_length, packet_type, packet_identifier):
        if packet_type == "data":
            print "data"
            packet_decoded = SerialInterface.recover_original_packet(byte_array[self.HEADER_LENGTH:], packet_length)
            if packet_decoded == 0:
                self.request_retransmission(packet_identifier)
                return
            current_packet = struct.unpack('H', byte_array[5:7])[0]
            message_id = struct.unpack('B', byte_array[4:5])[0]
            last_packet = struct.unpack('H', byte_array[7:9])[0]
            self.send_acknowledgement(packet_identifier)
            # TODO: If I actually lose the first packet but receive the second, what can I do about it?
            if current_packet == 1:
                if last_packet != 1:
                    self.message_dict[message_id] = packet_decoded + bytearray((last_packet - 1) * self.MAX_PACKET_LENGTH)
                    self.received_packet_status[message_id] = [True] + [False] * (last_packet - 1)
                else:
                    self.message_queue.put(packet_decoded)
                    print last_packet, current_packet
                    print self.input_queue.qsize()
                    return
            elif self.received_packet_status.has_key(message_id):
                self.received_packet_status[message_id][current_packet - 1] = True
                if current_packet == last_packet:
                    self.message_dict[message_id][(current_packet - 1) * self.MAX_PACKET_LENGTH:] = packet_decoded
                else:
                    self.message_dict[message_id][(current_packet - 1) * self.MAX_PACKET_LENGTH: current_packet * self.MAX_PACKET_LENGTH] = packet_decoded
                if not self.received_packet_status[message_id][current_packet - 1]:
                    retransmit_packet = current_packet - 1
                    packet_identifier = struct.unpack('I', bytearray(struct.pack('B', message_id)) + bytearray(struct.pack('H', current_packet)) + bytearray(1))
                    self.request_retransmission(packet_identifier)
                    while not self.received_packet_status[message_id][retransmit_packet - 1]:
                        retransmit_packet = current_packet - 1
                        packet_identifier = struct.unpack('I', bytearray(struct.pack('B', message_id)) + bytearray(struct.pack('H', current_packet)) + bytearray(1))
                        self.request_retransmission(packet_identifier)
            print last_packet, current_packet
            print self.input_queue.qsize()
            if self.received_packet_status.has_key(message_id) and all(self.received_packet_status[message_id]):
                print "getting message"
                self.message_queue.put(self.message_dict.pop(message_id), block=False)
                self.received_packet_status.pop(message_id)
        elif packet_type == "acknowledge":
            print "ack"
            if self.packet_timer_dict.has_key(packet_identifier):
                self.packet_timer_dict[packet_identifier][1].cancel()
                self.packet_timer_dict.pop(packet_identifier)
            else:
                print "Timer doesnt exist"
            if self.in_window_packets_dict.has_key(packet_identifier):
                self.in_window_packets_dict.pop(packet_identifier)
            else:
                print "No packet in window dict"
            self.window_slots_left += 1
            print self.window_slots_left
        elif packet_type == "retransmission":
            print "ret"
            if self.packet_timer_dict[packet_identifier][0] == 1:
                return
            self.packet_timer_dict[packet_identifier][1].cancel()
            self.retransmit_ack_queue.put(self.in_window_packets_dict[packet_identifier], block=False)
            self.retransmit_ack_queue.put(bytearray(struct.pack('I', packet_identifier))[:-1], block=False)

                            #       --HEADER--
#       \packet_begin(4 bytes)\message_id(1 byte)\current_packet(2 bytes)\last_packet(2 bytes)\packet_length(2 bytes)\
#       --/HEADER--

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
    def request_retransmission(self, packet_identifier):
        packet = bytearray(struct.pack('I', self.RETRANS_PACKET_B)) + bytearray(struct.pack('I', packet_identifier))
        packet = packet[:-1]
        self.retransmit_ack_queue.put(packet)
        print "ask for retransmission"

    def send_acknowledgement(self, packet_identifier):
        packet = bytearray(struct.pack('I', self.ACK_PACKET_B)) + bytearray(struct.pack('I', packet_identifier))
        packet = packet[:-1]
        self.retransmit_ack_queue.put(packet)
        print "sending ack"
        # print packet
        return



