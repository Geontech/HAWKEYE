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
@summary: REDHAWK Service proxy
"""

from core import RH_Message, Proxy_Base
from port import Port

from ossie.utils import redhawk

class Service(Proxy_Base):    
    def _finish_init_(self):
        for p in self._obj.ports:
            self._children.append(Port(p, self, self._outbox))
    
    def _getID(self):
        return self._obj._get_identifier()
    
    def getMessage(self, change='update'):
        return RH_Message(change, 
                          'service', 
                          self.getID, 
                          self._obj.name,
                          {'parentID' : self._parent.getID})
    
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

