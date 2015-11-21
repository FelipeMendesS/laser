import unittest
from serialData import SerialInterface
import os
import random

class serialDataTest(unittest.TestCase):

    def test_error_detection(self):
        for i in range(100, 64000, 1000):
            a = bytearray(os.urandom(i))
            b = SerialInterface.include_error_correction(a)
            self.assertEqual(SerialInterface.real_packet_length(i), len(b))
            c = SerialInterface.recover_original_packet(b, i)
            self.assertEqual(c, a)

    def test_error_detection_with_errors(self):
        a = bytearray(os.urandom(50000))
        b = SerialInterface.include_error_correction(a)
        for i in range(6):
            k = random.randint(0, len(b))
            for i in range(100):
                b[k+i] = 0
        c = SerialInterface.recover_original_packet(b, 50000)
        self.assertEqual(c, a)
