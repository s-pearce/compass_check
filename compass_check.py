#! /usr/bin/python

"""compass_check
    Determines the quality and drift of a compass calibration on a Slocum G2
    electric glider.
"""

import re
import sys
import os
import os.path
import time
import optparse
#import pdb
import cPickle as cp
from datetime import datetime as dt
import numpy as np
import matplotlib.pyplot as plt
import serial.tools.list_ports as lp
from exceptions import Exception

from cc.parse_options import parser
from cc.serial_rf import GliderRF
from cc.dockserver_com import dockserverCom

VERSION = '1.0'

# NOTES:  Add a save pickle so that if program fails, data is not lost, and
# when started back up can check and announce preserved data.
TSTAMP = dt.utcnow()
DATESTR = TSTAMP.strftime('%Y-%m-%d')
TIMESTR1 = TSTAMP.strftime('%H%M')
TIMESTR2 = TSTAMP.strftime('%H:%M')

PRINT_ROW_INFO = [  # (row header, format, data dict key)
    ('Pedestal Heading:', '%6d', 'pedestal_deg'),
    ('Glider True Heading:', '%6d', 'glider_true_deg'),
    ('Compass Magnetic Reading:', '%6.2f', 'compass_mag_deg'),
    ('Compass True Heading:', '%6.2f', 'compass_true_deg'),
    ('Error:', '%6.2f', 'error')]


class CompassRangeError(Exception):
    pass


def redtext(mesg):
    """Displays a message on stdout in red text.
    """
    if sys.platform == 'win32':
        import win32console
        handle = win32console.GetStdHandle(win32console.STD_OUTPUT_HANDLE)
        reset = handle.GetConsoleScreenBufferInfo()['Attributes']
        handle.SetConsoleTextAttribute(12)
        sys.stdout.writelines(mesg+'\n')
        handle.SetConsoleTextAttribute(reset)
    else:
        sys.stdout.write('\033[91m'+mesg+'\033[0m\n')


def list_ports():
    """Display a list of list of available serial ports on the local machine
    """
    print '\nHere is the list of available ports on this machine:'
    # lp.comports returns a list of (port, description, hardware ID) tuples
    iterator = sorted(lp.comports())
    for port, desc, hwid in iterator:
        print port
    exit()


def check_heading(heading):
    """Check that an compass heading value is formatted to a proper
    compass range of -180 to 180 degrees or 0 to 360 degrees.
    """
    if not (heading >= -180 and heading <= 360):
        raise CompassRangeError(
            'Not in a valid compass range of -180 to 180 degrees, or '
            '0 to 360 degrees')


class pickler():
    """Pickler handles persistance of data in case of a failed or aborted
    compass check.
    """
    def __init__(self, compass_data):
        self.cd = compass_data
        gname = compass_data.gname
        homedir = os.path.expanduser("~")
        if not os.path.exists(homedir + '/.cc'):
            os.mkdir(homedir + '/.cc')
        drctry = homedir + '/.cc/'
        self.pickle_name = drctry + gname + '_cc_' + DATESTR + '.pckl'

    def read(self):
        try:
            pickle = open(self.pickle_name, 'rb')
        except IOError:
            pickle = None
        if pickle:
            with pickle:
                self.cd.data, self.cd.mag_var = cp.load(pickle)
            print 'Loaded previously saved data.'
            self.cd.print_headings()
            return True
        else:
            return False

    def remove(self):
        try:
            os.remove(self.pickle_name)
        except:
            pass

    def write(self):
        pickle = open(self.pickle_name, 'wb')
        with pickle:
            cp.dump((self.cd.data, self.cd.mag_var), pickle)


class CompassData():
    def __init__(self, glidername, host_port, offset, n_samples=10,
                 serialCom=False, verbose=False, debug=False):
        self.n_samples = n_samples
        self.gname = glidername
        self.offset = offset
        self.verbose = verbose
        self.debug = debug
        self.fname = self.gname + '_cc_' + DATESTR + '_' + TIMESTR1
        self.data = {}

        # bind the data persistor (pickler) and check for any saved data.  If
        # any, pickler loads it into self.data
        loaded = False
        self.pickler = pickler(self)
        loaded = self.pickler.read()
        print 'Saved Data has been loaded.'

        # setup appropriate communication system with glider
        if serialCom:
            self.glider = GliderRF(glidername, host_port, verbose, debug)
        else:
            self.glider = dockserverCom(glidername, host_port, verbose, debug)

        # --Begin collecting data--
        self.headings = []
        with self.glider:
            if not loaded:
                self.mag_var = self.glider.get_mag_var()
            self.config_check()
            print '\nMove glider to initial heading'
            self.pd_hdg = self.input_pedestal_heading()
            while self.pd_hdg is not None:
                self.get_compass_point()
                print '\nMove glider to next heading'
                self.pd_hdg = self.input_pedestal_heading()

    def get_compass_point(self):
        """ Gathers heading data from the glider and calculates the error for
        a single compass point.
        """
        # read headings from glider source (serial Freewave or Dockserver)
        hdgs = self.glider.read_headings(self.n_samples)

        # --Calculations--
        # compass headings added together need to be kept in the correct
        # compass ranges (0-360, 0-2*pi) and so uses mod (%) 360 or 2*pi
        avg_hdg = np.mean(hdgs)
        g_true_deg = self.pd_hdg + self.offset
        avg_deg = np.rad2deg(avg_hdg)
        true_rad = (avg_hdg + self.mag_var) % (2*np.pi)
        true_deg = np.rad2deg(true_rad)
        comp_error = ((g_true_deg - true_deg + 180) % 360) - 180

        # --Write to self.data dictionary--
        data = {}
        data['compass_sample_rad'] = hdgs
        data['pedestal_deg'] = self.pd_hdg
        data['glider_true_deg'] = g_true_deg % 360.
        data['compass_mag_rad'] = avg_hdg
        data['compass_mag_deg'] = np.rad2deg(avg_hdg)
        data['compass_true_rad'] = true_rad
        data['compass_true_deg'] = true_deg
        data['error'] = comp_error
        self.print_sample(data)
        self.data[self.pd_hdg] = data
        self.pickler.write()

    def input_pedestal_heading(self):
        reply_ok = False
        while not reply_ok:
            hdg = raw_input(
                "\nOnce glider is in position and magnetic fields are away, "
                "\nenter the pedestal heading in positive degrees\nand hit "
                "return to continue.\nType d to view data and q to quit:\n>> ")
            #pdb.set_trace()
            if hdg == 'q':
                hdg = None
                reply_ok = True
                self.pickler.remove()
            elif hdg == 'd':
                self.print_headings()
            else:
                try:
                    hdg = int(hdg)
                except ValueError:
                    redtext('Answer is not a valid number.')
                    continue
                if hdg >= 0 and hdg <= 360:
                    reply_ok = True
                else:
                    redtext('Enter a valid compass heading (0-360 degrees)')
        return hdg

    def config_check(self):
        """Have the user view and verify the values used for offset and
        magnetic declination, and allow a chance to change the values.
        """
        print 'Using Values:'
        print '  offset = %.1f deg' % self.offset
        print('  magnetic declination = %.2f deg (%.3f rad)'
              % (np.rad2deg(self.mag_var), self.mag_var))
        print 'Press enter to continue with these values or e to edit them'
        edit_reply = raw_input('>> ')
        if edit_reply == 'e':
            for name in ['offset', 'mag dec']:
                change_value = False
                while True:
                    value_reply = raw_input(
                        'Enter a new %s value, or press enter to '
                        'keep the current value\n%s = ' % (name, name))
                    if not value_reply == '':
                        try:
                            new_value = float(value_reply)
                            check_heading(new_value)
                        except ValueError:
                            redtext('Value not a valid number')
                            continue
                        except OffsetRangeError:
                            redtext(
                                'Not in the valid range of '
                                '-180< offset <180 degrees.')
                            continue
                        change_value = True
                        break
                    else:
                        change_value = False
                        break
                if change_value:
                    if name == 'offset':
                        self.offset = new_value
                    elif name == 'mag dec':
                        self.mag_var = new_value

    def print_sample(self, data):
        sys.stdout.write('Offset: %.1f; ' % self.offset)
        sys.stdout.write('Magnetic Declination: %.2f\n' % np.rad2deg(self.mag_var))
        max_len = max(map(lambda x: len(x[0]), PRINT_ROW_INFO))
        for row_header, fmt, dat_key in PRINT_ROW_INFO:
            # print row header
            lead_space = ' ' * (max_len - len(row_header))
            sys.stdout.write(lead_space + row_header)
            # print row data
            #pdb.set_trace()
            write_str = ' ' + fmt + '\n'
            sys.stdout.write(write_str % data[dat_key])
        # print sample data gathered
        lead_space = ' ' * (max_len - 5)
        sys.stdout.write(lead_space + 'Data:')
        for ii in range(self.n_samples):
            if ii > 0:
                sys.stdout.write(' ' * max_len)
            comp_dat = data['compass_sample_rad'][ii]
            sys.stdout.write(' %6.2f\n' % comp_dat)

    def print_headings(self):
        """Prints to the screen the final data set after collection in 6
        columns at a time.
        """
        hdg_list = sorted(self.data.keys())
        sys.stdout.write('Offset: %.1f; ' % self.offset)
        sys.stdout.write('Magnetic Declination: %.2f\n' % np.rad2deg(self.mag_var))
        # get maximum length of row headers for lining up everything
        max_len = max(map(lambda x: len(x[0]), PRINT_ROW_INFO))
        while hdg_list:
            # this part ensures printing only 6 columns at a time to prevent
            # text from wrapping when printed to a terminal
            if len(hdg_list) > 6:
                last = 6
            else:
                last = len(hdg_list)
            hdgs = hdg_list[0:last]
            # pop the headings used in HDGS out of HDG_LIST
            hdg_list[0:last] = []

            # Printing handled
            for row_header, fmt, dat_key in PRINT_ROW_INFO:
                # print row header
                lead_space = ' ' * (max_len - len(row_header))
                sys.stdout.write(lead_space + row_header)
                # print row data
                #pdb.set_trace()
                for hdg in hdgs:
                    sys.stdout.write(' '+fmt % self.data[hdg][dat_key])
                sys.stdout.write('\n')
            # print sample data gathered
            lead_space = ' ' * (max_len - 5)
            sys.stdout.write(lead_space + 'Data:')
            for ii in range(self.n_samples):
                if ii > 0:
                    sys.stdout.write(' ' * max_len)
                for hdg in hdgs:
                    comp_dat = self.data[hdg]['compass_sample_rad'][ii]
                    sys.stdout.write(' %6.2f' % comp_dat)
                sys.stdout.write('\n')
            sys.stdout.write('\n')  # add a line between sections

    def plot_data(self):
        errors = []
        headings = []
        for key in self.data:
            errors.append(self.data[key]['error'])
            headings.append(self.data[key]['glider_true_deg'])
        if len(headings) > 1:
            plt.stem(headings, errors, 'b:', 'bo', 'k-')
            plt.xlim(-5, 365)
            estd = np.std(errors)
            plt.ylim(min(errors) - estd/4, max(errors) + estd/4)
            plt.title(self.gname + ' ' + DATESTR + ' ' + TIMESTR2)
            plt.xlabel('Glider True Heading, [degrees]')
            plt.ylabel('Heading error, [degrees]')
            plt.savefig('./' + self.fname + '.png')
            plt.show()
        else:
            sys.stdout.write('Warning: Not enough data to make a plot!\n')

    def write_data(self):
        fid = open(self.fname + '.csv', 'w')
        hdg_list = sorted(self.data.keys())
        with fid:
            fid.write(','.join([
                self.gname, 'Compass Check', DATESTR, TIMESTR2,
                'Offset:', '%d deg' % self.offset,
                'Declination:', '%.2f deg' % np.rad2deg(self.mag_var)]))
            fid.write('\n\n')
            for row_header, fmt, dat_key in PRINT_ROW_INFO:
                fid.write(row_header)
                for hdg in hdg_list:
                    fid.write(',' + fmt % self.data[hdg][dat_key])
                fid.write('\n')
            fid.write('Data:')
            for ii in range(self.n_samples):
                for hdg in hdg_list:
                    fid.write(',%6.2f' % self.data[hdg]['compass_sample_rad'][ii])
                fid.write('\n')


def main():
    print os.getcwd()
    print 'Compass Accuracy Check v. %s' % VERSION
    (options, args) = parser.parse_args()
    if options.list_ports:
        list_ports()
    if len(args) < 2:
        redtext('\nCompass check requires 2 arguments\n')
        parser.print_help()
        exit()

    host_port = args[0]
    glidername = args[1]
    offset = options.offset
    if not offset == 0.0:
        check_heading(offset)
    cd = CompassData(
        glidername, host_port, offset,
        serialCom=options.serial,
        verbose=options.verbose,
        debug=options.debug)
    cd.print_headings()
    cd.plot_data()
    cd.write_data()
    #print 'Soon to include graphics too.'

if __name__ == '__main__':
    main()

