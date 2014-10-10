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
@summary: ZeroRPC Frontend Example
"""
from rh_gateway import RH_Gateway

import sys
import gevent
import zerorpc
import logging
import signal
import os
import time

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
def Outbound(callback, address=None):
    client = zerorpc.Client()
    if client:
        client.connect(address)
        while True:
            try:
                messages = callback()
                if (0 < len(messages)):
                    client.passMessages(messages)
            except:
                pass
            finally:
                gevent.sleep(0)

class Inbound(object):
    def __init__(self, callback):
        self._callback = callback
    def passMessages(self, messages):
        return self._callback(messages)
    
# ZeroRPC server wrapping the RH_Gateway
# gevent used to help manage the ZeroRPC greenlet thread.
if __name__ == '__main__':
    logging.basicConfig()
    logger = logging.getLogger('zerorpc')
    logger.setLevel(logging.INFO)
    if (len(sys.argv) > 1):
        # Create greenlets for the inbound and outbound workers.  Use the 
        # gateway's sendMessages and getMessages methods as callbacks
        try:
            logger.info("Initializing RH Gateway")
            gw = RH_Gateway()
            gw.start()
            
            logger.info("Spawning ZeroRPC Outbound Client")
            ge_outbound = gevent.spawn(Outbound, gw.getMessages, sys.argv[1] + "_node2rh")
            
            logger.info("Spawning ZeroRPC Inbound Server")
            zpc = zerorpc.Server(Inbound(gw.sendMessages))
            
            logger.info("ZeroRPC Bridge Starting")
            zpc.bind(sys.argv[1] + "_rh2node")
            gevent.signal(signal.SIGTERM, zpc.stop)
            gevent.signal(signal.SIGINT, zpc.stop)
            zpc.run()   # Blocks here until the ZPC stops.
            
            try:
                logger.info("RH Gateway shutting down ZeroRPC Client")
                ge_outbound.kill();
                gevent.joinall([ge_outbound])
                os.remove(sys.argv[1].replace("ipc://","") + "_rh2node");
            except: 
                logger.warning("RH Gateway error in closing down ZPC Client")
                raise
        except Exception as e:
            logger.warning("Exception raised {0}".format(e.args))
        finally:
            # Attempt to clear IPC artifact from system.
            logger.info("RH Gateway Exiting")
            sys.exit();
        
    else:
        logger.error("The gateway requires a base socket address for 2-way communication.")
        logger.error("\tFor example: rh_gateway 'ipc://./mysocket.sock'")
