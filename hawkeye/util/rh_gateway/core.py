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

Core definitions for the gateway, messaging, and proxies.
"""

""" Description of messaging between client and gateway:
 * 
 * Message prototype for exchanges between browser and session
 * @param change - '', 'add', 'remove', 'update'
 * @param rhtype - 'domain', 'device_manager', 'device', 'service', 
 *                 'application', 'component', 'port', 'property', ''
 * @param rhid - a unique ID for rhtype in question
 * @param more - an associative array of any additional data pertaining to 
 *               this message.  Reserved key is 'parentID' which should be
 *               this rhid's parent's rhid.
 *
 * Example:  
 *          Client Sends           Client Receives array of entities
 *      { change: 'add',         [{ change: 'add',
 *        rhtype: 'domain',         rhtype: 'domain',
 *        rhid:   '',               rhid:   'domain_id_#1',
 *        rhname: '',               rhname: 'domain_name',
 *        more: {} }                more:   {} }, ..., {}]
"""
def RH_Message(change='', rhtype='', rhid='', rhname='', more={}):
    msg = {"change":change, "rhtype":rhtype, "rhid":rhid, "rhname":rhname, "more":{'parentID':''}}
    msg['more'].update(more)
    return msg

import sys
import time
import logging
import threading

# Abstract base class for proxies
class Proxy_Base(object):    
    """
    No real need to override.  Just use _finish_init_() to do anything
    special required of the subclass.  "Private" variables are:
    
        _obj will be its REDHAWK instance object
        _parent will be its parent's Proxy_Base object
        _outbox is the queue to use for async messaging (put(msgarray))
        _children[] is an array of Proxy_Base objects contained in this one.
        _id is the REDHAWK-unique ID of this object.
        _name is the REHAWK instance's "name" (e.g., Device.name, Port._name, etc.)
        _domain_id is the ID of the REDHAWK Domain to which this entity belongs.
        _timer is a handle to a timed task thread, if running, for periodic tasks
        _timerPeriodSec is the period, in seconds, of that task.
    
    @param rh_obj The REDHAWK Object for this object.
    @param rh_parent The Proxy_Base subclass that is the parent (container) 
                     of this object in REDHAWK.
    @param outbox The Queue to use for any async updates (if necessary)
    """
    def __init__(self, rh_obj=None, rh_parent=None, outbox=None):
        if (None == rh_obj):
            raise Exception("Unable to create object without a redhawk reference object.")
        elif (None == rh_parent):
            raise Exception("Unable to create object without a redhawk parent Proxy object.")
        elif (None == outbox):
            raise Exception("Unable to create object without a Queue outbox.")
        
        self._obj = rh_obj
        self._parent = rh_parent
        self._outbox = outbox
        self._children = []
        self._id = ''
        self._name = ''
        self._domain_id = ''
        self._timer = None
        self._oneshotTimer = None
        self._timerPeriodSec = 1.0
        
        self._logger = None
        self.allDescendentIDs = []
        
        # Announce creation and then finish init.
        self.sendMessages([self.getMessage('add')])
        self._finish_init_()
    
    @property
    def _log(self):
        if not self._logger:
            self._logger = logging.getLogger(type(self).__name__)
            self._logger.setLevel(logging.INFO)
        return self._logger
    
    """
    Fetch the domain ID, from the parent if necessary.
    """
    @property
    def getDomainID(self):
        if ('' == self._domain_id):
            return self._parent.getDomainID
        else:
            return self._domain_id
        
    
    """
    Do not override.  External objects will call this to locate this proxy and it should always 
    have a valid value.  Override _getID() to get the identifier from the unique RH instance.
    """
    @property
    def getID(self):
        try:
            if (None != self._getID):
                self._id = self._getID;
        finally:
            return self._id
    
    """
    Do not override.  External objects will call this to get the "name" of the REDHAWK object.
    Override the _getName method otherwise.  Method ensures this always returns the last valid
    value just in case the REDHAWK object being tapped in self._getName is touched.
    """
    @property
    def getName(self):
        try:
            if (None != self._getName):
                self._name = self._getName
        finally:
            return self._name
    
    """
    Do not override.  Method is a frontend for routing incoming message processing to lower
    levels of hierarchy.  Implement _processThisMessage() to handle incoming messages per this class.
    @param message The RH_Message to process.
    @return array of RH Message (either empty array or populated with objects).
    """
    def processMessage(self, message):
        msgs = []
        # Message is to this object.
        if (message['rhid'] == self.getID):
            msgs += self._processThisMessage(message)
            
        # Message is to a descendent, perhaps.
        else:
            c = [c for c in self._children if c.getID == message['rhid']]
            if (1 == len(c)):
                msgs += c[0].processMessage(message)
                
            elif (message['more']['parentID'] in self.allDescendentIDs):
                for c in self._children:
                    msgs += c.processMessage(message)
        return msgs
    
    """
    Do not override...And don't use if you can avoid it.
    It's not efficient, but is an effective means of helping the processMessage() routing system.  
    Per message received at the Domain level, a refresh will be requested throughout the system.
    """
    def updateDescendentIDs(self):
        ids = []
        for c in self._children:
            ids.append(c.getID)
            c.updateDescendentIDs();
            ids += c.allDescendentIDs;
        self.allDescendentIDs = ids;
    
    """
    Do not override.  Method does an "update from here" message starting at this point in the 
    REDHAWK Hierarchy and out towards descendents.
    """
    def getUpdateFromHere(self, change):
        msgs = [self.getMessage(change)]
        for c in self._children:
            msgs += c.getUpdateFromHere(change)
        return msgs
    
    """
    Do not override.  Call this method to kick-off a periodic task (_timer) timed to 
    the update rate specified by _timerPeriodSec.  This method calls _doPeriodicTask()
    and re-schedules the event.
    """
    def doPeriodicTask(self):
        self._doPeriodicTask()
        self._timer = threading.Timer(self._timerPeriodSec, self.doPeriodicTask)
        self._timer.start()
    
    """
    Do not override.  Call this method to fire _doPeriodicTask() once after some number
    of seconds (which can be a fraction)
    """
    def doPeriodicTaskOnceAfter(self, sec):
        if (None != self._oneshotTimer):
            self._oneshotTimer.cancel()
            
        self._oneshotTimer = threading.Timer(sec, self._doPeriodicTask)
        self._oneshotTimer.start()
    
    """
    Do not override.  Simply stops (kills) the timer running the periodic task.
    """
    def stopPeriodicTask(self):
        if (None != self._timer):
            self._timer.cancel()
            self._timer = None
    
    """
    Do not override.  Ensures the following:
      1) Calls _cleanUp() on this instance (can be overridden)
      2) Kills the built-in periodic task if running
      3) Calls cleanUp() on any children
      4) Sends a 'remove' message for this entity to the client.
    """
    def cleanUp(self):
        self._cleanUp()
        self.stopPeriodicTask()
        if (None != self._oneshotTimer):
            self._oneshotTimer.cancel()
        for c in self._children:
            c.cleanUp()
        self._children = []
        self.sendMessages([self.getMessage('remove')])
    
    
    """
    Wrapper for the outbox to ensure the timer sleeps before
    async transmissions back to the client.  
    """
    def sendMessages(self, msgarray):
        for m in msgarray:
            self._outbox.put(m)
        time.sleep(0)
    
    """
    --- IMPLEMENT THE FOLLOWING ---
    """
    
    """
    Be careful when overriding -- this method may be called when the REDHAWK object 
    is no longer valid (i.e., during 'remove' changes)!  
    @return A single RH_Message describing this object using any specified change.
    """
    def getMessage(self, change='update'):
        raise Exception("Class did not implement _getMessage")
    
    """
    Method only called once at __init__.  Should finish init of the object and populate 
    _children with any Proxy_Base objects created in the process.
    """
    def _finish_init_(self):
        raise Exception("Class did not implement _finish_init_")
    
    
    """
    @return the unique ID of this REDHAWK object (_get_identifier(), etc.)
    """
    @property
    def _getID(self):
        return self._obj._get_identifier()

    """
    @return the name of this REDHAWK object (name, etc.)
    """
    @property
    def _getName(self):
        return self._obj.name

    """
    Process a message, however that should be for the class Return an array of RH_Message 
    if necessary or an empty array.
    @param message The RH_Message to process
    @return array Array of RH_Message or an empty array.
    """
    def _processThisMessage(self, message):
        return []
    
    """
    Periodic task to perform if doPeriodicTask() was ever called.
    """
    def _doPeriodicTask(self):
        pass
    
    """
    Clean up function (in case any gevent greenlets need to be killed, etc.
    Should call cleanUp on each child if this object has children.
    """
    def _cleanUp(self):
        return

if __name__=="__main__":
    logging.getLogger().setLevel(logging.INFO)
