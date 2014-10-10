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
@summary: Frontend example using STDIN and STDOUT for message exhanges
"""

from rh_gateway import RH_Gateway

# `sys` for flushing stdout
# `json` for converting the RH_Message list between strings/object format.
# `gevent, signal, fcntl, os` all related to the read/write through the gateway.
import sys
import json
import gevent
from gevent.socket import wait_read
import signal
import fcntl
import os
import logging

"""
This worker attempts to readline() from STDIN and pass any resulting messages
to the inbox.  This has been adapted from: https://gist.github.com/tmc/787105
"""
def inboundWorker(callback):
    fcntl.fcntl(sys.stdin, fcntl.F_SETFL, os.O_NONBLOCK)
    while True:
        wait_read(sys.stdin.fileno())
        line = sys.stdin.readline()
        try:
            messages = json.loads(line)
            callback(messages) # Into the RH_Gateway
        except:
            logging.warning("Dropped bad JSON string from input")
        gevent.sleep(0)

"""
This worker listens to the outbox and forwards anything found to STDOUT
"""
def outboundWorker(callback):
    while True:
        messages = callback()
        if (0 < len(messages)):
            print(json.dumps(messages)); sys.stdout.flush();
        gevent.sleep(0)

"""
Spawn greenlets and wait (joinall)
"""
if __name__ == '__main__':
    logging.getLogger('std_front').setLevel(logging.INFO)
    try:
        gw = RH_Gateway()
        gw.start()
        ge_inbox = gevent.spawn(inboundWorker, ge_gateway.sendMessages)
        ge_outbox = gevent.spawn(outboundWorker, ge_gateway.getMessages)

        # Capture interruptions/exits
        gevent.signal(signal.SIGTERM, ge_inbox.kill)
        gevent.signal(signal.SIGINT, ge_inbox.kill)
        gevent.signal(signal.SIGTERM, ge_outbox.kill)
        gevent.signal(signal.SIGINT, ge_outbox.kill)
        
        # Wait...
        gevent.joinall([ge_inbox, ge_outbox])
    except:
        raise
    finally:
        # Clean-up
        gw.stop()
    
