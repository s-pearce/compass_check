""" serial_rf.py
Implements a glider radio frequency (RF, usually Freewave brand) connection
through a serial port connection on the local computer (not a dockserver).

The implementation here is specifically an RF connection intended for checking
the accuracy of the glider's compass.
"""
import serial
import time
import re
import numpy as np
from exceptions import Exception
#import pdb

# regex to grab the heading
heading_regex = r'.+sensor: m_heading = (\d\.*\d*) rad'
hdg_matcher = re.compile(heading_regex)

# regex to grab the magnetic variance
get_value_regex = r' = (-*\d+\.*\d+) \w*'
gv_matcher = re.compile(get_value_regex)


class GliderConfigureException(Exception):
    pass


class SerialPortConfigureException(Exception):
    pass


class GliderRF():
    '''Class GliderRF handles the serial port communication with a glider
    over a Freewave RF modem.

    Specifically, the glider should be setup so that the compass heading is
    reporting every cycle (i.e. report ++ m_heading), and in GliderLAB (i.e.
    lab_mode on).
    '''
    def __init__(self, glidername, port, verbose=False, debug=False):
        #pdb.set_trace()
        self.name = glidername
        self.verbose = verbose
        self.debug = debug
        self.port = port.upper()
        if debug:
            print 'Attempting connection with serial port %s' % self.port
        try:
            self.ser = serial.Serial(self.port, 115200, timeout=1)
        except:
            raise SerialPortConfigureException(
                '\nCannot open serial port %s.  Check ports and connection and '
                'try again.' % self.port)
        #pdb.set_trace()
        #time.sleep(1)
        if self.ser.isOpen():
            self.verify_serial()
            print 'Connection to port %s successful' % self.port

    def verify_serial(self):
        hdg_present = False  # is m_heading present in the output?
        lab_on = False   # is the glider in lab_mode?
        readable = False  # is the serial output human readable and expected?
        for tries in range(3):  # give it 3 tries before raising exceptions
            self.write('')
            time.sleep(0.3)
            lines = self.ser.readlines()
            for line in lines:
                if not hdg_present:
                    if 'm_heading' in line:
                        hdg_present = True
                        readable = True
                if not lab_on:
                    if 'GliderLAB' in line:
                        lab_on = True
                        readable = True
                if hdg_present and readable and lab_on:
                    if self.debug:
                        print 'Port configured correctly and Glider setup correctly.'
                    return True
        if readable and (not lab_on or not hdg_present):
            raise GliderConfigureException(
                'Serial port correct, but Glider maybe incorrectly '
                'configured.\nI.e. GliderLAB on, and m_heading reporting.  '
                'Check glider and try again.')
        else:
            raise SerialPortConfigureException(
                'Serial port appears to be configured incorrectly.  '
                'Characters are not what is expected.')

    # write a command to the glider
    def write(self, command_string):
        """Writes a command to the glider and append the end of line
        character, \r
        """
        for char in command_string:
            self.ser.write(char)
        self.ser.write('\r')

    # read COUNT number of lines and get the headings out
    def read_headings(self, count=10):
        """  Read COUNT number of lines of output and get compass heading data.
        """
        headings = []
        hdg_lines = []
        othr_lines = []
        line_count = 0
        self.ser.flushInput()
        while line_count < count:
            line = self.ser.readline().replace('\r\n', '')
            if line:
                print line
                match = hdg_matcher.match(line)
                if match:
                    if self.debug:
                        print '  parsed heading = ', match.group(1)
                    hdg_lines.append(line)
                    headings.append(float(match.group(1)))
                    line_count += 1
                else:
                    othr_lines.append(line)
        if self.verbose:
            print '\nAdditional Output:'
            for line in othr_lines:
                print line
            print 'Heading Output:'
            for line in hdg_lines:
                print line
        return headings

    def get_mag_var(self, try_lines=3):
        match = None
        while not match:
            self.ser.flushInput()
            time.sleep(0.1)
            self.write('get m_gps_mag_var')
            line1 = self.ser.readline().replace('\r\n', '')
            if self.debug:
                print line1
            tries = 0
            while tries < try_lines:
                line2 = self.ser.readline().replace('\r\n', '')
                if self.debug:
                    print line2
                match = gv_matcher.match(line2)
                tries += 1
                if self.debug:
                    print 'Try #%d of %d' % (tries, try_lines)
                if match:
                    if self.debug:
                        print 'mag_var regex matched'
                    mag_var = float(match.group(1))
                    if self.debug:
                        print 'mag_var = %f radians' % -mag_var
                    break
        return -mag_var  # the gliders handle mag_var negatively

    def __enter__(self):
        """Enter code used in a "with" statement for the serial port.
        """
        return self

    def __exit__(self, etype, evalue, etraceback):
        """Exit code used in a "with" statement for the serial port
        """
        self.ser.close()
