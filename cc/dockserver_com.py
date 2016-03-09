#!/usr/bin/env python
from dockserverTalk.dockserverTalk import ThreadedDockserverComm
from dockserverTalk.dialogues import Buffer
import re
import time

# regex to grab the heading
heading_regex = r'.+sensor: m_heading = (\d\.*\d*) rad'
hdg_matcher = re.compile(heading_regex)

# regex to grab the magnetic variance
mag_var_regex = r' = (-*\d+\.*\d+) rad'
mv_matcher = re.compile(mag_var_regex)


class ccBuffer(Buffer):
    def __init__(self,dockserverComm):
        Buffer.__init__(self,dockserverComm)
        # when we put data on the queue, and someone
        # is reading out the queue, we use the name
        # of the glider as identifier.
        self.glider=dockserverComm.gliderName
        self.MPQueue=dockserverComm.MPQueue

    # override the add method.
    def add(self,mesg):
        self+=mesg # note that self is a list.
        while True:
            # getCompleteLine is a method of Buffer and subclassed.
            # this method returns a complete line (incl. CR) or an
            # empty string
            mesg=self.getCompleteLine()
            if mesg=='':
                break
            # We have something to write. Let's put it into the dockserver's
            # Message Passing Queue
            self.MPQueue.put((self.glider,mesg))


class dockserverCom():
    """
    """
    def __init__(self, glidername, hostname, verbose=False, debug=False):
        self.name = glidername
        self.verbose = verbose
        self.debug = debug
        self.hostname = hostname
        self.port = 6564
        self.senderID = "compass-check;0x001cc"
        self.dc = ThreadedDockserverComm(
            hostname, glidername, self.port, self.senderID, debug=self.debug)
        self.dc.connect_bufferHandler(ccBuffer)
        self.dc.start()
        if not self.dc.isAlive():
            raise IOError("DockserverComm instance didn't start up.")
        if self.verbose:
            print 'Connected to Dockserver', self.hostname
        # want to verify the glider config here?

    def write(self, command_string):
        """
        """
        # if nothing else is added to this method, it should be removed and
        # the dc.sendCommand used instead
        self.dc.sendCommand(command_string)
        if self.verbose:
            print 'Wrote command:', command_string

    def flush(self):
        """
        """
        self.dc.MPQueue.queue.clear()
        if self.dc.MPQueue.empty():
            return True

    def read_headings(self, count=10):
        """
        """
        headings = []
        line_count = 0
        if self.verbose:
            print 'Gathering %d headings.' % count
        # flush buffer so headings aren't old
        flushed = self.flush()
        while flushed:
            if not self.dc.MPQueue.empty():
                while not self.dc.MPQueue.empty():
                    gliderName, mesg = self.dc.MPQueue.get_nowait()
                    print mesg.rstrip()
                    match_hdg = hdg_matcher.match(mesg)
                    if match_hdg:
                        hdg = float(match_hdg.group(1))
                        headings.append(hdg)
                        line_count += 1
            else:
                time.sleep(0.5)
            if line_count >= count:
                break
        return headings

    def get_mag_var(self, try_lines=3):
        """
        """
        # flush queue buffer
        match_mv = None
        tries = 0
        flushed = self.flush()
        while not match_mv:
            self.write('get m_gps_mag_var')
            tries = 0
            while tries <= try_lines:
                if not self.dc.MPQueue.empty():
                    while not self.dc.MPQueue.empty():
                        gliderName, mesg = self.dc.MPQueue.get_nowait()
                        if self.verbose:
                            print mesg.rstrip()
                        match_mv = mv_matcher.match(mesg)
                        tries += 1
                        if match_mv:
                            if self.verbose:
                                print 'Matched mag var'
                            mag_var = float(match_mv.group(1))
                            return -mag_var
                else:
                    # Sleep to not overrun CPU cycles
                    time.sleep(0.1)
        return -mag_var

    def close(self):
        """An interactive method to close the dockserver connection
        """
        self.dc.terminate()
        self.dc.join()

    def __enter__(self):
        """Enter method to use for a ``with`` statement
        """
        return self

    def __exit__(self, etype, evalue, etraceback):
        """Exit code used in a ``with`` statement
        """
        self.flush()
        self.dc.terminate()
        self.dc.join()
        if self.verbose:
            print 'Exited Gracefully!'

