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
@summary: REDHAWK Component and Device proxies
"""

from core import RH_Message, Proxy_Base
from port import Port

import ossie.properties as ossie_prop
from ossie.utils import redhawk

import string, sys

"""
Base class from which Component and Device derive since they're very similar.
NOTE: getMessage appends `more` with:
      `usageState` ==> IDLE/ACTIVE/BUSY
      `started`    ==> true/false
"""
class CompDev_Base(Proxy_Base):
    def _finish_init_(self):
        for p in self._obj.ports:
            self._children.append(Port.getPort(p, self, self._outbox))
        for prop in self._obj._propertySet:
            try:
                pp = Property(prop, self, self._outbox)
                self._children.append(pp)
            except:
                pass
    
    def getMessage(self, change='update'):
        msg = RH_Message(change, 
                         string.lower(self.__class__.__name__), 
                         self.getID, 
                         self.getName, 
                         {'parentID': self._parent.getID})
        return msg

    def _processThisMessage(self, message):
        # TODO: What other kinds of messages does this entity require?  Start/Stop?
        if ('update' == message['change']):
            if (0 == len(self._children)):
                # Should have children.  Reattempt _finish_init_()
                self._finish_init_()
            return self.getUpdateFromHere('update')
        # default response
        return []
        
    def _cleanUp(self):
        pass
    

"""
Component Proxy class
"""
class Component(CompDev_Base):
    pass


"""
Device Proxy class
"""
class Device(CompDev_Base):
    def getMessage(self, change='update'):
        msg = CompDev_Base.getMessage(self, change)
        if ('remove' != change):
            msg['more'].update({'usageState': "{0}".format(self._obj.usageState), 
                                'started': "{0}".format(self._obj._get_started())})
        return msg
    

"""
Property Proxy class
NOTE: 1) Object obtained from dev/comp._propertySet[index].
      2) getMessage adds fields to `more`:
            `value`  ==> ... The value of the property
            `access` ==> readwrite, readonly, writeonly
      3) Property ID's are only unique within the parent (not the whole domain)
         so the getID will prefix the Parent's ID with its own.
"""
class Property(Proxy_Base):
    def _finish_init_(self):
        self._nextValue = None
    
    @property
    def _getID(self):
        return self._parent.getID + '.' + self._obj.id
    
    @property
    def _getName(self):
        return self._obj.clean_name
    
    def getMessage(self, change='update'):
        msg = RH_Message(change, 'property', 
                         self.getID,
                         self.getName, 
                         {'parentID': self._parent.getID})
        if ('remove' != change):
            msg['more'].update({'value': self._obj.queryValue(),
                                'access': self._obj.mode})
        return msg
    
    # Periodic task has 2 tasks: If a next value exists, configure it.  In any case, send an update.
    # the update either confirms the value was accepted or proves it was rejected (via the UI).
    def _doPeriodicTask(self):
        try:
            if None != self._nextValue:
                print("Setting property value..."); sys.stdout.flush()
                self._obj.configureValue(self._nextValue)
                self._nextValue = None
                print("Successfully set value."); sys.stdout.flush()
            
        except Exception as e:
            print("Failed to set property type: " + self._obj.type); sys.stdout.flush()
            print(e); sys.stdout.flush();
            
        finally:
            # Kick out an update to the client.
            if self._streaming():
                self.sendMessages([self.getMessage('stream')])
            else:
                self.sendMessages([self.getMessage('update')])
    
    def _processThisMessage(self, message):
        if ('update' == message['change']):
            # Set the property.
            self._nextValue = self._coerceValue(message['more']['value'])
            # Emit delayed acknowledgement
            if not self._streaming():
                self.doPeriodicTaskOnceAfter(1.0)
        elif ('start' == message['change']) and not self._streaming:
            self._start()
            return [self.getMessage('stream')]
        elif ('stop' == message['change']) and self._streaming:
            self._stop()
            return [self.getMessage('update')]
        # default response
        return []
    
    # FIXME: struct, sequence, etc. do not work.
    def _coerceValue(self, newValue):
        if ('struct' == self._obj.type):
            return newValue
        elif ('sequence' == self._obj.type):
            return newValue
        elif ('structSeq' == self._obj.type):
            return newValue
        else:
            return ossie_prop.to_pyvalue(newValue, self._obj.type)
        
    def _streaming(self):
        return (None != self._greenlet)
    
    def _start(self):
        self.doPeriodicTask()
    
    def _stop(self):
        self.stopPeriodicTask()

    def _cleanUp(self):
        if (self._streaming):
            try:
                self._stop()
            except:
                # FIXME: come up with a way to clean-exit on a failed stream.
                pass 
