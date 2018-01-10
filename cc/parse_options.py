#!/usr/bin/env python

import optparse

"""Creates the input options and help description for the Compass
Check program.
"""

parser = optparse.OptionParser(
    usage=(
        "\n    Dockserver: %prog [options] hostname glidername\n"
        "   Serial Port: %prog [options] -s port glidername"),
    description=(
        """Glider Compass Accuracy Check: Performs a glider compass accuracy
        check by comparing the internal compass heading to known true headings.
        compass_check can communicate over either a dockserver connection
        (default), or a serial port with a Freewave modem connected. For full
        instructions view the README.TXT file that came with this program."""))

parser.add_option(
    "-s", "--serial",
    help=(
        "Connect through an RF modem using a serial port. "
        "To find available serial ports, use either:"
        '"python -m serial.tools.list_ports", '
        "or use the --list_ports option alone in this program"),
    dest="serial",
    action='store_true')

parser.add_option(
    "-o", "--offset",
    help=(
        "Add an offset between the glider's compass heading and "
        "the pedestal's compass heading in degrees. "
        "Offset is positive if the glider is rotated right of the "
        "pedestal heading direction; negative if rotated left."),
    dest="offset",
    default=0.0,
    action='store',
    type=float)

parser.add_option(
    "-m", "--magvar",
    help=(
        "Manually add the magnetic variation/declination (the"
        "difference between Magnetic North and True North for "
        "the location).  The program tries to get this from the"
        "glider otherwise."
        "Note: Enter the opposite sign as printed by the glider." 
        "TWR handles this incorrectly."),
    dest="magvar",
    default=None,
    action='store',
    type=float)

parser.add_option(
    "-v",
    help="Verbosity.  Explicitly print program actions.",
    dest="verbose",
    default=False,
    action='store_true')

parser.add_option(
    "--debug",
    help="print debug messages and tracebacks (development mode)",
    dest="debug",
    default=False,
    action='store_true')

parser.add_option(
    "--list-ports",
    help=("list available serial ports on this machine."),
    dest="list_ports",
    action='store_true')

if __name__ == '__main__':
    (options, args) = parser.parse_args()
    print '\nOptions:'
    print options
    print '\nArgs:'
    print args
    print 'length of args:'
    print len(args)

