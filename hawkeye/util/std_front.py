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
import threading
import time
import signal
import os
import logging
import traceback

"""
Thread-safe STDIN reader
"""
class STDINReader(threading.Thread):
    LOCK = threading.Lock()
    def __init__(self, callback):
        threading.Thread.__init__(self)
        self.callback = callback
        self._event = threading.Event()
    
    def run(self):
        while True:
            time.sleep(1)
            if self.stopped:
                return
            for line in sys.stdin:
                try: 
                    messages = json.loads(line)
                    time.sleep(1.0)
                    with self.LOCK:
                        self.callback(messages) # Into the RH_Gateway
                except:
                    logging.error("Inbound message delivery failure\nLine:{0}\nException {1}".format(
                        line,
                        traceback.format_exc()))
    def stop(self):
        self._event.set()
    @property
    def stopped(self):
        return self._event.isSet()

"""
Thread-safe STDOUT writer
"""
class STDOUTWriter(threading.Thread):
    LOCK = threading.Lock()
    def __init__(self, callback, limit=0):
        threading.Thread.__init__(self)
        self.callback = callback
        self.limit = limit
        self._event = threading.Event()
        
    def run(self):
        while True:
            time.sleep(1.0)
            if self.stopped:
                return
            messages = self.callback(self.limit)
            if 0 < len(messages):
                time.sleep(1.0)
                with self.LOCK:
                    print(json.dumps(messages, sort_keys=True)) # Out of the RH_Gateway
    def stop(self):
        self._event.set()
    @property
    def stopped(self):
        return self._event.isSet()


if __name__ == '__main__':
    logging.basicConfig()
    logger = logging.getLogger('std_front')
    logger.setLevel(logging.INFO)
    try:
        Gateway = RH_Gateway()
        Reader = STDINReader(Gateway.sendMessages)
        Writer = STDOUTWriter(Gateway.getMessages, 1)
        
        Gateway.start()
        Reader.start()
        Writer.start()
        logger.info('Interface to RH Gateway started')
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt, IOError:
        logger.info('RH Gateway received notice to shutdown.')
    except:
        logger.error('RH Gateway STDIN/OUT Exception: {0}'.format(traceback.format_exc()))
    finally:
        Gateway.stop()
        while not Gateway.stopped:
            time.sleep(0.5)
        Reader.stop()
        Reader.join()
        Writer.stop()
        Writer.join()
        
        # Gateway Join is not necessary
        logger.info('RH Gateway stopped')
        sys.exit()
    
