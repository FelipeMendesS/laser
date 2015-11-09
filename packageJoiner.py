import serial
import matplotlib.pyplot as plt
# import numpy as np
import threading
import time
import Queue
import struct

class PackedJoiner(object):
	"""docstring for PackedJoiner"""
	def __init__(self, arg):
		self.input_queue = Queue.Queue()
        self.output_queue = Queue.Queue()
        self.message_queue = Queue.Queue()
		