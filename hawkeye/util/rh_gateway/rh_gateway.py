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

@summary: Classes for managing the two ZeroRPC client-server relationships.
"""
from core import RH_Message
from domain import Domain
from utilities import *

from ossie.utils import redhawk

import sys, gevent, zerorpc, json, signal, string, os
from gevent.queue import Queue


"""
Method for receiving messages from the RH Gateway and sending them back
over to the ZeroRPC Server instance at the RH Session Node.js side.
Each item placed in the outbox is (should be) an array of RH_Message.

This outbox is at this time shared across all Proxy_Base entities for
asynchronous communication.  ZeroRPC may deadlock if all attempt to 
access the queue at once from, effectively, the same greenlet.  This
is mitigated by collecting all queued messages into a single payload
delivered as often as possible.
"""
def clientWorker(outbox=None, address=None):
    client = zerorpc.Client()
    if (None != client) and (None != outbox):
        client.connect(address)
        while True:
            try:
                # Concat all items in queue into same array to
                # be more efficient in delivering several messages.
                messages = []
                while not outbox.empty():
                    messages += outbox.get()
                if (0 < len(messages)):
                    client.passMessages(messages)
            except:
                pass
            finally:
                gevent.sleep(0)


"""
Class for acting as the ZeroRPC Server on the Python side.
"""
class RH_Gateway(object):
    def __init__(self, outbox=None):
        self.outbox = outbox
        
        # List of domain being maintained for incoming messages
        self._domains = []
        
        # Kick-off async scanning for domain changes
        self.domainTask = None
        self._domainListMessages = []
        self._domainTaskWaitSec = 1
        self.domainTask = gevent.spawn_later(self._domainTaskWaitSec, self._domainListCheck)
        
        print("RH Gateway started successfully."); sys.stdout.flush()
    
    def __del__(self):
        try:
            print("RH Gateway closing down..."); sys.stdout.flush()
            self.domainTask.kill()     
            for d in self._domains:
                d.cleanUp()
            self._domains = []
        except:
            print("RH Gateway caught exception"); sys.stdout.flush()
            raise
    
    # Message handler to accept commands, from the client browser via the 
    # ZeroRPC intermediary session configured in the Node.js Server.
    # ZeroRPC already translated the JSON string back into our RH_Message
    # dictionary (hopefully).
    #
    # Note: For rhtypes application, device_manager, device, service, and 
    #    component, the provided msg['data'][0] will be used as the parentID
    #    to allow the client to enforce their own hierarchy.  The RH_Gateway
    #    will always initially encourage the real system hierarchy on its
    #    first 'add' of each rhtype.
    # 
    # @param messages RH_Message list to process from the ZeroRPC client
    #
    # @return retMessages The messages if any, None otherwise.
    #
    # TODO: Add error checking to make sure messages is a RH_Message list.
    def passMessages(self, messages):        
        print ("RH Gateway received messages: ")
        print (messages); sys.stdout.flush();
        
        retMessages = []
        for msg in messages:
            if (None == msg):
                print("WARNING: Client included an empty entry in its messages; skipping it."); sys.stdout.flush()
                continue
            
            # Attempt to forward the message to each domain.
            # FIXME: This does not account for identical IDs in different domains.
            for d in self._domains:
                d.updateDescendentIDs() # Costly... find a better way.
                retMessages += d.processMessage(msg)
                
        if (0 == len(retMessages)):
            return None;
        else:
            return retMessages;
    
    # ####################################################################
    # !!! NOTE: Methods prefixed with '_' are not visible through ZeroRPC 
    # ####################################################################
    
    # Scans the domain for changes, creates instances, and queues the next scan..
    def _domainListCheck(self):
        newList = self._getMessagesForDomainListing('add')
        adds, removes = splitDictLists(newList, self._domainListMessages, RH_Message().keys())
        
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
                                        self.outbox))                # Using the global outbox
        
        self._domainListMessages = newList;
        self.domainTask = gevent.spawn_later(self._domainTaskWaitSec, self._domainListCheck)
    
    
    # Gets a list of active REDHAWK Domains and returns each as a message.
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
        except Exception as e:
            print("Caught exception while scanning REDHAWK CORE...never good.")
            print("---> Forcing a reset of the RH_Gateway."); sys.stdout.flush()
            self.close()
            
        finally:
            return msgs
    

    
# ZeroRPC server wrapping the RH_Gateway
# gevent used to help manage the ZeroRPC greenlet thread.
if __name__ == '__main__':
    if (len(sys.argv) > 1):
        # Create a queue and a gevent greenlet for the second ZeroRPC instance
        # Spawn and connect the two instances by the queue.
        try: 
            q = Queue();
            ge_client = gevent.spawn(clientWorker, q, sys.argv[1] + "_node2rh")
            zpc = zerorpc.Server(RH_Gateway(q))     
            zpc.bind(sys.argv[1] + "_rh2node")
            
            gevent.signal(signal.SIGTERM, zpc.stop)
            gevent.signal(signal.SIGINT, zpc.stop)
            
            zpc.run()   # Blocks here until the ZPC stops.
            
            try:
                print("RH Gateway shutting down ZRPC Client");
                ge_client.kill();
                gevent.joinall([ge_client])
                os.remove(sys.argv[1].replace("ipc://","") + "_rh2node");
            except Exception as e: 
                print("RH Gateway error in closing down ZPC Client: "); 
                print(e); sys.stdout.flush();
            
        finally:
            # Attempt to clear IPC artifact from system.
            print("RH Gateway Exiting"); sys.stdout.flush()
            sys.exit();
        
    else:
        print("ERROR: The gateway requires a base socket address for 2-way communication.")
        print("\tFor example: rh_gateway 'ipc://./mysocket.sock'"); sys.stdout.flush()
