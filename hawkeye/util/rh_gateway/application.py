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
@summary: REDHAWK Application (waveform) proxy
"""

from core import RH_Message, Proxy_Base
from comp_dev import Component

from ossie.utils import redhawk

# Message includes 'running' state (True if started, False otherwise).
class Application(Proxy_Base):    
    def _finish_init_(self):
        for c in self._obj.comps:
            self._children.append(Component(c, self, self._outbox))
    
    def getMessage(self, change='update'):
        message =  RH_Message(change, 
                          'application', 
                          self.getID, 
                          self.getName,
                          {'parentID': self._parent.getID})
        if ('remove' != change):
            message['more'].update({'running' : self._obj._get_started()})
        return message;
    
    def _processThisMessage(self, message):
        # TODO: What other kinds of messages does this entity require?
        if ('update' == message['change']):
            if (0 == len(self._children)):
                # Should have children.  Reattempt _finish_init_()
                self._finish_init_()
            return self.getUpdateFromHere('update')
        elif ('start' == message['change']) and not self._obj._get_started():
            self._obj.start();
            return [self.getMessage()]
        elif ('stop' == message['change']):
            if (self._obj._get_started()):
                self._obj.stop();
                return [self.getMessage()]
            else:
                self._obj.releaseObject();
                
        # default response
        return []
    
    def _cleanUp(self):
        pass