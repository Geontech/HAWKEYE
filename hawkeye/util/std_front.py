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
import traceback

"""
This worker attempts to readline() from STDIN and pass any resulting messages
to the inbox.  This has been adapted from: https://gist.github.com/tmc/787105
"""
def inboundWorker(callback):
    fcntl.fcntl(sys.stdin, fcntl.F_SETFL, os.O_NONBLOCK)
    while True:
        wait_read(sys.stdin.fileno())
        line = sys.stdin.readline()
        if 0 < len(line):
            try:
                messages = json.loads(line)
                callback(messages) # Into the RH_Gateway
            except:
                logging.error("Inbound message delivery failure\nLine:{0}\nException {1}".format(
                    line,
                    traceback.format_exc()))
        gevent.sleep(0.25)

"""
This worker listens to the outbox and forwards anything found to STDOUT
"""
def outboundWorker(callback):
    while True:
        messages = callback() # From the RH_Gateway
        if (0 < len(messages)):
            print(json.dumps(messages));
        gevent.sleep(0.25)

"""
Spawn greenlets and wait (joinall)
"""
if __name__ == '__main__':
    logging.basicConfig()
    logger = logging.getLogger('std_front')
    logger.setLevel(logging.INFO)
    try:
        gw = RH_Gateway()
        gw.start()
        ge_inbox = gevent.spawn(inboundWorker, gw.sendMessages)
        ge_outbox = gevent.spawn(outboundWorker, gw.getMessages)
        logger.info('Interface to RH Gateway created')

        # Capture interruptions/exits
        gevent.signal(signal.SIGTERM, ge_inbox.kill)
        gevent.signal(signal.SIGINT, ge_inbox.kill)
        gevent.signal(signal.SIGTERM, ge_outbox.kill)
        gevent.signal(signal.SIGINT, ge_outbox.kill)
        
        # Wait...
        logger.info('Interface RH Gateway ready')
        gevent.joinall([ge_inbox, ge_outbox])
        logger.info('Interface to RH Gateway closed')
    except:
        logger.error('RH Gateway STDIN/OUT Exception: {0}'.format(traceback.format_exc()))
    finally:
        # Clean-up
        gw.stop()
        logger.info('RH Gateway stopped')
    
