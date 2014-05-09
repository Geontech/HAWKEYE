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
@summary: REDHAWK Device Manager (Node) proxy
"""

from core import RH_Message, Proxy_Base
from comp_dev import Device
from service import Service

from ossie.utils import redhawk

class Device_Manager(Proxy_Base):    
    def _finish_init_(self):
        for d in self._obj.devs:
            self._children.append(Device(d, self, self._outbox))
        for s in self._obj.services:
            self._children.append(Service(s, self, self._outbox))
    
    def getMessage(self, change='add'):
        return RH_Message(change, 
                          'device_manager', 
                          self.getID, 
                          self.getName, 
                          {'parentID': self._parent.getID})
    
    def _processThisMessage(self, message):
        # TODO: What other kinds of messages does this entity require?
        if ('update' == message['change']):
            if (0 == len(self._children)):
                # Should have children.  Reattempt _finish_init_()
                self._finish_init_()
            return self.getUpdateFromHere('update')
        # default response
        return []
    
    def _cleanUp(self):
        pass