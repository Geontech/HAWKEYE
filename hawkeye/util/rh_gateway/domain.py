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
@description
   REDHAWK Domain proxy object.
"""

from core import RH_Message, Proxy_Base
from device_manager import Device_Manager
from application import Application

from ossie.utils import redhawk
from ossie.utils.redhawk.channels import ODMListener
from ossie.utils.weakobj import WeakBoundMethod

import time, string, sys


# REDHAWK Domain object.
class Domain(Proxy_Base):
    """
     * OVERRIDES
    """    
    def _finish_init_(self):
        # Connect ODM callbacks, create device managers and waveforms
        self._odm = ODMListener()
        self._domain_id = self.getID
        for node in self._obj.devMgrs:
            self._children.append(Device_Manager(node, self, self._outbox))       
        for wave in self._obj.apps:
            self._children.append(Application(wave, self, self._outbox))
        self.__connect_channels__()
    
    def getMessage(self, change='change'):
        return RH_Message(change, 'domain', self.getID, self.getName)
    
    def _processThisMessage(self, message):
        # TODO: What kinds of messages would a domain process from the client?
        if ('update' == message['change']):
            return self.getUpdateFromHere('update')
        # default response
        return []
    
    def _cleanUp(self):
        try:
            self._odm.disconnect()
        except:
            pass
    
    """
     * ADDONS
    """
    
    def __connect_channels__(self):
        try:            
            # Connect to events on ODM channel
            self._odm.connect(self._obj)
            self._odm.deviceManagerAdded.addListener(WeakBoundMethod(self.__ODM_Added))
            self._odm.deviceManagerRemoved.addListener(WeakBoundMethod(self.__ODM_Removed))
            #self._odm.deviceAdded.addListener(WeakBoundMethod(self.__ODM_Added))
            #self._odm.deviceRemoved.addListener(WeakBoundMethod(self.__ODM_Removed))
            #self._odm.serviceAdded.addListener(WeakBoundMethod(self.__ODM_Added))
            #self._odm.serviceRemoved.addListener(WeakBoundMethod(self.__ODM_Removed))
            #self._odm.applicationFactoryAdded.addListener(WeakBoundMethod(self.__ODM_Added))
            #self._odm.applicationFactoryRemoved.addListener(WeakBoundMethod(self.__ODM_Removed))
            self._odm.applicationAdded.addListener(WeakBoundMethod(self.__ODM_Added))
            self._odm.applicationRemoved.addListener(WeakBoundMethod(self.__ODM_Removed))
        except:
            raise Domain('Unable to connect to domain to listeners')
    
    """
     *  ODM Event Callbacks
     *  ODM Event: producerId, sourceId, sourceName, sourceCategory
     *     Notes: 1) Ignoring sourceIOR stringified object.
     *            2) These are async callbacks to the parent and therefore
     *               invoke passMessages via ZeroRPC.
     *  The 2 second delay is to let the Domain's model catch up with the 
     *  faster incoming ODM events.
     *
     *  Possible evt.sourceCategories are: device_manager, device, 
     *  application_factory, application, and service.  The Domain
     *  only needs to listen for the top-level Device Manager and 
     *  Application events since each entity will handle their children,
     *  respectively.
    """        
    def __ODM_Added(self, evt):
        time.sleep(2)
        rhtype = string.lower("{0}".format(evt.sourceCategory))
        if ('device_manager' == rhtype):
            for dm in self._obj.devMgrs:
                if (dm._get_identifier() == evt.sourceId):
                    self._children.append(Device_Manager(dm, self, self._outbox))
        elif ('application' == rhtype):
            for wave in self._obj.apps:
                if (wave._get_identifier() == evt.sourceId):
                    self._children.append(Application(wave, self, self._outbox))
        
    """
     *  ODM "Removed" listener.  Only responds to device_manager and application
     *  event categories since the Domain prunes the top-level entity.
    """
    def __ODM_Removed(self, evt):
        rhtype = string.lower("{0}".format(evt.sourceCategory))
        if ('device_manager' != rhtype) and ('application' != rhtype):
            return
        
        idx = -1
        for i, c in enumerate(self._children):
            if (evt.sourceId == c.getID):
                idx = i
                c.cleanUp()
                break
        if (-1 != idx):
            del self._children[idx]
