# compass_check
**A program to check the accuracy of the compass values on a Slocum G2 electric glider.**

*Compass_check* records compass measurements reported by a glider while it is rotated though a number of known azimuths, characterizing the compass errors, and writes the results to a CSV file and a PNG plot image.  It is able to connect to the glider on a computer that has Dockserver running on it, a computer connected remotely to a Dockserver, or a computer with serial connection to the Freewave modem and a serial terminal emulator (such as [Tera Term](https://ttssh2.osdn.jp/index.html.en)).


#####Dependencies
*Compass_check* requires the [Numpy](http://www.numpy.org/) and [Matplotlib](http://matplotlib.org/) packages.
Additionally, the [Dockserver-talk](https://sourceforge.net/projects/dockserver-talk/) package, written by Lucas Merckelbach, is required; installed and available on the Python path (i.e. importable by Python).

#####Installation
To install, simply download and use the compass_check software right away, or install it to the python site-packages using:
```
python setup.py install
```
I currently advocate just downloading and using the compass_check.py from the downloaded folder as I haven't tested the install in the site-packages location much.  I don't think there is anything that would be weird, however, permissions could affect file creation for the results.

Make sure that when you dowload, you keep the `cc` directory in the same directory as `compass_check.py` if you move the files around.  There are .py files that are called from there.

I like to keep it in a separate source directory in my home directory and create a soft link in a *bin* directory, also in my home, that is on my path and name the link `compass_check`.

#####Usage
* Dockserver on remote computer: 
```
compass_check.py [options] <hostname> <glidername>
```
* Dockserver on local computer: 
```
compass_check.py [options] localhost <glidername>
```
* Serial Port: 
```
compass_check.py [options] -s <port> <glidername>
```
These use the system python, otherwise call your python installation of choice with `python compass_check.py`
Make sure Dockserver-talk, Numpy, and Matplotlib are available to whichever Python install you use.  It is common on Linux distributions to have a system python and your own version you like to use, but crossing over the 2 can cause problems.

To read the help and see what options are available use:
```
compass_check.py -h
```

#####Instructions
Setup your Freewave connection to your glider, power on, and gain control of the glider after bootup.  The glider should be in lab mode and have the Iridium and Argos turned off with either
```
put c_iridium_on -1
put c_argos_on -1
```
or 
```
use - argos iridium
```
first so they don't interrupt the compass check and second since we are concerned about the compass while diving, we want the glider in a similar state where Argos and Iridium are turned off.  We will turn off GPS, but first we need to get the magnetic declination.  Use the `put c_gps_on 3` command and wait until a GPS signal is aquired (the `V` changes to an `A`).  Once a position is aquired, turn off the GPS with `put c_gps_on -1`.  For stringency, it would be prudent to turn on the scientific instruments so that their magnetic fields are present too.  You can do so simply by using `put c_science_all_on 0`.  Report the glider's compass heading by using `report ++ m_heading`.  

If you are using a serial port connection to the glider, after getting the glider in lab mode and reporting heading, you should close the terminal emulator to free up the port for *compass_check*.  If you are using a Dockserver connection (or locally), you can run *compass_check* in a terminal while leaving Glider Terminal open.  Run *compass_check* following the usage above.  *Compass_check* will then gather the magnetic declination from the glider and ask you if it and the offset values are reasonable (you should know what the magnetic declination is for your region).  The offset is what the compass stand reading is compared to the actual direction the glider is pointing.  For example, with our compass checking aimed at true North, the glider attached to the stand can either point East or West, for an offset of +90° or -90° respectively.  This is somewhat built into the software for legacy use, but may find usefullness elsewhere too.  Most likely though offset will be 0 for most people, where the glider points at the same direction as the non-glider direction measurement, which can be markings on the ground, a stand registered to directions, dual GPS receivers, or a hand held compass.  Whichever method is used though, the known direction (nonglider measure) should be in True earth direction, meaning the magnetic declination has been removed.  Perhaps in a future revision I will make an option for inputing magnetic handheld compass readings.  

After the program prints the declination and offset values, you can accept these values by pressing enter, or edit them; just follow the on screen instructions.  Once the values are correct, the program will ask that you move the glider to a known heading, and enter it on the screen in degrees from 0-359 in true earth compass direction.  Once entered, the program will read the `m_heading` measurements, average the data, and calculate the error.  The results will be printed to the screen for that direction, and you will be asked for the next direction measurement.  Rotate the glider to the next known direction, enter it, and the program will gather and calculate the next error.  Continue this until you have a sufficient number of directions to characterize the compass circle; there is no limit to the number of directions you can measure.  If while measuring a direction, you would like to measure the same direction again, it will overwrite your first measurement of that direction.  Once you have all of the directional measurements you want, just press `q` instead of a direction and it will print a summary of the results to the screen and make a plot of the errors at the directions.  Once you close the plot, the results are written to a comma separated values (CSV) file and the plot saved as a PNG image file; the file names will be `[glidername]_cc_yyyy-mm-dd` where yyyy is the year, mm is the month number and dd is the day.

After program completion, reconnect to the glider via the serial terminal emulator, or bring Glider Terminal back up to get back to controlling the glider and you can shut down the glider.

Note: If you are using a serial connection and are uncertain of the port name/number, you can call the `--list-ports` option e.g. `compass_check.py --list-ports` to print out a list of available serial ports.
