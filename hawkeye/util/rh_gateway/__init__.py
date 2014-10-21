"""
Copyright: 2014 Geon Technologies, LLC

This file is part of HAWKEYE.

HAWKEYE is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.


@author Thomas Goodwin
@summary: The gateway module provides access to the REDHAWK Model via proxy objects
  to handle the specifics of each entity type (Domain vs. Device, etc.).
"""
from core import RH_Message
from domain import Domain
from utilities import *

from ossie.utils import redhawk

import logging
import time
import threading
import traceback
from Queue import Queue

"""
Class for acting as the main bridge to any Domain in the naming service.

Instantiate this class and use start() and 
stop() to manage the traffic interface.  Messages can be sent/received using
sendMessages() and getAllMessages() (for bulk send/receive).
"""
class RH_Gateway(object):
    def __init__(self, maxQueueSizes=500):
        self._log = logging.getLogger(type(self).__name__)
        self._log.setLevel(logging.INFO)
        
        if 100 > maxQueueSizes:
            maxQueueSizes = 100
            self._log.warning("maxQueueSizes should be greater than 100, but something your system can support.")
            
        self._inbox = Queue(maxQueueSizes)
        self._outbox = Queue(maxQueueSizes)
        
        # List of domains being maintained for incoming messages
        self._domains = []
        
        # Scanning for domain changes and resulting list.
        self._domainListMessages = []
        self._domainScanningPeriod = 1
        self._domainScanningTimer = None
        
        self._runLock = threading.Lock()
        self._running = False
        self._runThread = None
        self._runPeriod = 0.25
        
        self._getCallback = None
        
        self._log.info("RH Gateway initialized successfully.");
    
    def __del__(self):
        try:
            self._log.info("RH Gateway closing down...")
            self.stop()
            for d in self._domains:
                d.cleanUp()
            self._domains = []
        except:
            self._log.error("RH Gateway caught exception on shutdown: {0}".format(traceback.format_exc()))
            raise
    
    """
    Assign a callback for "getMessages" which will empty the out-going queue
    into the callback when it is non-empty.
    """
    def useCallbackForGet(self, callback):
        self._getCallback = callback
    
    """
    Returns 'True' if message was sent, 'False' otherwise.
    """
    def sendMessages(self, messages):
        if not type(messages) == list:
            messages = [messages]
            
        for m in messages:
            if not self._inbox.full():
                self._inbox.put(m)
            else:
                self._log.warning("Incoming queue is full.  " + 
                    "Increase the size, send fewer, or run the RH Gateway "+
                    "on a faster system.")
                break
    
    """
    Returns a list of RH Messages (if any exist) or an empty list.
    """
    def getMessages(self):
        messages = []
        while not self._outbox.empty():
            messages.append(self._outbox.get())
        return messages
    
    @property
    def running(self):
        self._runLock.acquire()
        v = self._running
        self._runLock.release()
        return v
    
    @running.setter
    def running(self, val):
        self._runLock.acquire()
        self._running = val
        self._runLock.release()
    
    def start(self):
        self.running = True
        self._domainScanningTimer = threading.Timer(
            self._domainScanningPeriod, 
            self._domainScan)
        self._domainScanningTimer.start()
        self._runThread = threading.Thread(target=self._runLoop)
        self._runThread.daemon = True
        self._runThread.start()
    
    def stop(self):
        if self._domainScanningTimer:
            self._domainScanningTimer.cancel()
            self._domainScanningTimer = None
        self.running = False
        if self._runThread:
            self._runThread.join(5)
            self._runThread = None
    
    """
    Pushes messages from the inbox into the Domains; transfers any responses 
    to the outbox queue.
    """
    def _runLoop(self):
        while self.running:
            if not self._inbox.empty():
                msg = self._inbox.get()
                retMessages = []
                # Attempt to forward the message to each domain.
                # FIXME: This does not account for identical IDs in different domains.
                for d in self._domains:
                    d.updateDescendentIDs() # Costly... find a better way.
                    retMessages += d.processMessage(msg)
                # Push responses
                [self._outbox.put(o) for o in retMessages]
                
            # Forward outbox to callback, if created.
            if not self._outbox.empty() and self._getCallback:
                self._getCallback(self.getMessages())
                
            time.sleep(self._runPeriod)
    
    # Scans the domain for changes, creates instances, and queues the next scan..
    def _domainScan(self):
        newList = self._getMessagesForDomainListing('add')
        adds, removes = splitDictLists(newList, 
            self._domainListMessages, 
            RH_Message().keys())
        
        # Removals
        ids = [r['rhid'] for r in removes]
        indices = []
        if (0 < len(ids)):
            for i, d in enumerate(self._domains):
                if (d.getID in ids):
                    d.cleanUp()
                    indices.append(i)
            self._domains = [d for i, d in enumerate(self._domains) if i not in indices]
        
        # Additions
        for a in adds:
            self._domains.append(Domain(redhawk.attach(a['rhname']), # Return redhawk domain instance
                                        '',                          # No parent ID
                                        self._outbox))               # Using the global outbox
        
        self._domainListMessages = newList;
        self._domainScanningTimer = threading.Timer(
            self._domainScanningPeriod, 
            self._domainScan)
        self._domainScanningTimer.start()
    
    
    """
    Gets a list of active REDHAWK Domains and returns each as a message.
    """
    def _getMessagesForDomainListing(self, change='add'):
        msgs = []
        
        try:
            names = redhawk.scan()
            for name in names:
                d = redhawk.attach(name)
                id = d._get_identifier()
                msgs.append(RH_Message(change = change, 
                                       rhtype = 'domain', 
                                       rhid   = id, 
                                       rhname = name))
        except:
            self._log.error("Caught exception while scanning REDHAWK CORE: {0}".format(traceback.format_exc()))
            self._log.error("This usually happens when Omni services are unable to connect with the server.")
            
        finally:
            return msgs
