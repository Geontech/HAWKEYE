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

@author: Thomas Goodwin
@summary: REDHAWK Port proxy
"""

from core import RH_Message, Proxy_Base

from ossie.utils import redhawk
from ossie.cf import CF
from bulkio.bulkioInterfaces import BULKIO__POA
from omniORB import CORBA

import string, sys, json
from Queue import Queue
from threading import Lock

# For reshaping data streams
import numpy as np

class Port(Proxy_Base):
    """
    Returns a Port subclass more appropriately matching the type of the obj,
    for example BULKIO vs. a Frontend Interface.
    """
    @staticmethod
    def getPort(obj=None, parent=None, outbox=None):
        if (None == obj) or (None==parent) or (None == outbox):
            raise Exception("Port cannot be created without its RH instance, parent, and an outbox")
        
        category = obj._interface.nameSpace # FRONTEND, BULKIO, CF, etc.
        if (category == 'BULKIO'):
            return Port_BULKIO(obj, parent, outbox)
        elif (category == 'FRONTEND'):
            return Port_FRONTEND.getPort(obj, parent, outbox)
        else:
            return Port(obj, parent, outbox)
    """
    END of static helper.
    """
    
    
    """
    START - New overrides for Port class. 
    """
    # Called to "start" the stream.
    def _start(self):
        # Sends a "hello" message.  Default UI shows statistics if a 'stream' is received.
        self._isStreaming = True
    
    # Called to "stop" the stream.  Default UI shows a start button if 'update' is received.
    def _stop(self):
        self._isStreaming = False
    
    # Method should return True if streaming, False otherwise.
    @property
    def _streaming(self):
        return self._isStreaming
    """
    END - New overrides for port class.
    """
    
    """
    Overrides for Proxy_Base
    """
    def _finish_init_(self):
        self._isStreaming = False
    
    @property
    def _getID(self):
        # Port objects don't have an ID in REDHAWK so Port "ID" 
        # is made unique by the parent entity's ID and the port's name.
        return self._parent.getID + "." + self.getName
    
    @property
    def _getName(self):
        return self._obj._name
    
    """
    Ports return a message such that `more` includes 
       `storageType` ==> keys or value depending on what each `data` index represents in `data`.
                         Examples: keys would be an array of key-value pairs
                                   values would be an array of float numbers
       `direction` ==> uses/provides
       `nameSpace` ==> category of the port (FRONTEND, BULKIO, etc.).
       `data`      ==> vector of data items.
       
    When `start` is requested, the Port responds with an empty stream message.  When `stop`
    is received, the Port responds with an empty `update` message.  These are the 
    only acknowledgements common between these two implemented types.
    """
    def getMessage(self, change='update'):
        msg = RH_Message(change, 'port', self.getID, self.getName, {'parentID': self._parent.getID})
        if ('remove' != change):
            try: 
                msg['more'].update({'storageType': 'keys',  # Could be 'value' if data is a value array.
                                    'direction': self._obj._direction,
                                    'nameSpace': self._obj._interface.nameSpace,
                                    'data': []})
            except:
                pass
        return msg
    
    # Start/stop respond with an empty stream message (acknowledge) or update (finished)
    def _processThisMessage(self, message):
        if ('update' == message['change']):
            return self.getUpdateFromHere('update')
        elif ('start' == message['change']) and not self._streaming:
            self._start()
            return [self.getMessage('stream')]
        elif ('stop' == message['change']) and self._streaming:
            self._stop()
            return [self.getMessage('update')]
        # default response
        return []
    
    
    def _cleanUp(self):
        if (self._streaming):
            try:
                self._stop()
            except:
                # FIXME: come up with a way to clean-exit on a failed stream.
                pass 


"""
Different Port subclasses types
"""
"""
BULKIO - Messages are pushed from the RH model into the StreamHelper_* for
the appropriate data type.  A Queue.Queue is used to maintain a bridge
between the RH Model's thread and the main greenlet containing the Gateway.
Because of this, the BULKIO port runs a synchronous "pull" from the
stream helper which will return all messages received in the last interval.

The interval is set by to _timerPeriodSec which is not necessarily
an accurate/precise timer, but during testing even 0.000001 only yielded
a single packet delivered per pull period with a stream pushing >2MB of
samples in each packet.  Ultimately the inscessant "getMessages" call 
on the StreamHandler caused its queue to begin cascading.  A slower rate
introduced more stability despite delivering more messages at a time to
the client.
"""
class Port_BULKIO(Port):
    def _finish_init_(self):
        self._isStreaming = False
        self._timerPeriodSec = 0.25
        
        if ('Uses' == self._obj._direction):
            datatype = self._obj._using.filename
        else:
            datatype = self._obj._interface.filename
        
        if ('bio_dataShort' == datatype):
            self._helper = StreamHelper_Short(self)
        elif('bio_dataUshort' == datatype):
            self._helper = StreamHelper_Ushort(self)
        elif('bio_dataOctet' == datatype):
            self._helper = StreamHelper_Octet(self)
        elif('bio_dataLong' == datatype):
            self._helper = StreamHelper_Long(self)
        elif('bio_dataUlong' == datatype):
            self._helper = StreamHelper_Ulong(self)
        elif('bio_dataFloat' == datatype):
            self._helper = StreamHelper_Float(self)
        elif('bio_dataDouble' == datatype):
            self._helper = StreamHelper_Double(self)
        elif('bio_dataFile' == datatype):
            self._helper = StreamHelper_DataFile(self)
        else:
            # FIXME: Need more handlers...
            raise Exception("No stream handler for this type: " + datatype)
        
        orb = CORBA.ORB_init()
        self._poa = orb.resolve_initial_references("RootPOA")
        self._poaManager = self._poa._get_the_POAManager()
        self._poaManager.activate()
        self._poa.activate_object(self._helper)
        
        self._connectionID = self.getID + "_stream"
    
    def _cleanUp(self):
        Port._cleanUp(self)
        
    def getMessage(self, change):
        msg = Port.getMessage(self, change)
        msg['more']['storageType'] = 'value'
        return msg
        
    @property 
    def _streaming(self):
        return self._isStreaming
    
    def _start(self):
        self.doPeriodicTask()
        
    def _stop(self):
        self._obj.ref.disconnectPort(self._connectionID)
        self.stopPeriodicTask()
        self._isStreaming = False
    
    def _doPeriodicTask(self):
        if (0 == self._streaming):
            # Connect
            self._obj.ref.connectPort(self._helper._this(), self._connectionID)
            self._isStreaming = True
        else:
            # stream.
            messages = self._helper.getMessages()
            if (0 < len(messages)):
                self.sendMessages(messages)

""" 
FRONTEND Port type handler 
Interface is polled and pushed at a steady (slow) rate of roughly 1/4 sec.
This class uses the built-in Proxy_Base periodic task handler.

While it also supports the `stream` and `update` ack messages to start/stop, 
respectively, the client does not need to maintain a reciprocal message ack
to maintain the stream.
"""
class Port_FRONTEND(Port):    
    @staticmethod
    def getPort(obj=None, parent=None, outbox=None):
        if (None == obj) or (None==parent) or (None == outbox):
            raise Exception("Port cannot be created without its RH instance, parent, and an outbox")
        if ('GPS' == obj._interface.name):
            return Port_FRONTEND_GPS(obj, parent, outbox)
        else:
            #TODO: Add more types.
            return Port_FRONTEND(obj, parent, outbox)
    
    def _finish_init_(self):
        self._timerPeriodSec = 0.25
        
    @property
    def _streaming(self):
        return (None != self._timer)
    
    def _start(self):
        self.doPeriodicTask()
    
    def _stop(self):
        self.stopPeriodicTask()
    
    def _doPeriodicTask(self):
        # TODO: 1) Gather a dictionary of changes from the interface?
        #       2) self._outbox.put([msg]) the changes
        #       3) Respawn another callback.
        try:
            msg = self.getMessage('stream')
            msg['more']['data'] = self._getDataMessages()
            self._outbox.put([msg])
        except:
            # Exception likely because attached device is gone so stop
            # streaming.
            msg = self.getMessage('stop')
            self._processThisMessage(msg)
        
    """
    Overridden by subclasses, surely necessary.
    """
    def _getDataMessages(self):
        return ['hello']

class Port_FRONTEND_GPS(Port_FRONTEND):
    def _getDataMessages(self):
        pos = self._obj.ref._get_gps_time_pos().position
        messages = {'latitude': pos.lat, 
                    'longitude': pos.lon, 
                    'datavalid': pos.valid}
        return messages


"""
Helper classes for forwarding pushPacket requests off BULKIO ports.
The pushPacket appends the parent's message `more` field with new keys:
   `eos`       ==> true/false for End of Stream flag
   `stream_id` ==> The string ID of the stream per the model
   `sri`       ==> Contains `xdelta` and `mode` from the last SRI
   
TODO: Add data type field for value arrays.
TODO: Add ability to control reshaped width of each vector in the returned list (default 1024 now).
TODO: Add server-side DFT option to switch from raw data to Fourier output on the helper.
"""
class StreamHelper(object):
    def __init__(self, parent):
        self._queue = Queue(maxsize=50)
        self._parent = parent
        self._sri = None
        
    def pushSRI(self, H):
        pass
    
    # Greenlet-environment thread
    def getMessages(self):
        messages = [];
        while not self._queue.empty():
            messages += self._queue.get()
        return messages
    
    # REDHAWK-environment thread.  Reshape data to N rows of 1024 samples.
    def pushPacket(self, data, t_stamp, EOS, stream_id):
        msg = self._parent.getMessage('stream')
        data = np.reshape(data, (-1, 1024)).tolist()
        msg['more']['data'] = data;
        msg['more'].update({'eos': EOS, 
                            'stream_id': stream_id})
        
        if (self._sri):
            msg['more'].update({'sri': {'xdelta': self._sri.xdelta, 
                                       'mode': self._sri.mode}})
        try:
            self._queue.put([msg])
        except:
            # Likely full, roll new packet in.
            self._queue.get() 
            self._queue.put([msg])
            print("StreamHelper dropping a packet"); sys.stdout.flush()
    
    def pushSRI(self, sri):
        self._sri = sri;
        
# TODO: Create more StreamHelpers and add 'data type' to carry short, float, etc.
class StreamHelper_Short(BULKIO__POA.dataShort, StreamHelper):
    pass

class StreamHelper_Ushort(BULKIO__POA.dataUshort, StreamHelper):
    pass

class StreamHelper_Octet(BULKIO__POA.dataOctet, StreamHelper):
    pass

class StreamHelper_Long(BULKIO__POA.dataLong, StreamHelper):
    pass

class StreamHelper_Ulong(BULKIO__POA.dataUlong, StreamHelper):
    pass

class StreamHelper_Float(BULKIO__POA.dataFloat, StreamHelper):
    pass

class StreamHelper_Double(BULKIO__POA.dataDouble, StreamHelper):
    pass

class StreamHelper_DataFile(BULKIO__POA.dataFile, StreamHelper):
    pass
