import serial
import threading
import time
import Queue
import struct
from serialData import SerialInterface

class PacketJoiner(object):

    def __init__(self):

        self.joiner = threading.Thread(target=self.join_packets, args=self)
        self.joiner.start()




    # Function that has a thread for itself and keeps
    def join_packets():
        a = 1
        pass