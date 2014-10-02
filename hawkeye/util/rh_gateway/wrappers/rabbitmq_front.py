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
@summary: Frontend example using Pika (RabbitMQ/AMQP) for message exchanges
"""

import RH_Gateway
import pika
import logging
import time
import threading

class AMQPConnectionOption(object):
    exchange = ""
    exchange_type = ""
    routing_key_in = ""
    routing_key_out = ""
    url = "amqp://guest:guest@localhost"
    rx_queue_exclusive = True
    rx_queue_auto_delete = True
    exchange_passive = True
    
class AMQPBidirectional(object):
    def __init__(self, options=None, publish_cb, consume_cb):
        if not options:
            options = AMQPConnectionOptions()
        self._connection = None
        self._channel = None
        self._consumer_tag = ""
        self._closing = False
        self._options = options
        
        logging.getLogger(type(self).__name__).setLevel(logging.INFO)
        self._log = logging
        
    def connect(self):
        return pika.SelectConnection(
            pika.URLParameters(self._options.url), 
            self.on_connection_open, 
            stop_ioloop_on_close=False)
    
    def close_connection(self):
        self._log.info("Closing AMQP connection")
        self._closing = True
        if self._connection:
            self._connection.close()
    
    def reconnect(self):
        self._connection.ioloop.stop()
        if not self._closing:
            self._log.info("Reconnecting AMQP")
            self._connection = self.connect()
            self._connection.ioloop.start()
    
    def setup_exchange(self, exchange_name):
        self._log.info("Declaring Exchange")
        self._channel.exchange_declare(
            self.on_exchange_declareok,
            exchange_name,
            self._options.exchange_type,
            passive=self._options.exchange_passive)
    
    def setup_queue(self):
        self._log.info("Declaring Queue")
        self._channel.queue_declare(
            self.on_queue_declareok, 
            exclusive=self._options.rx_queue_exclusive,
            auto_delete=self._options.rx_queue_auto_delete)
    
    def enable_delivery_confirmations(self):
        self._channel.confirm_delivery(self.on_delivery_confirmation)
        
    def publish_message(self, body):
        if self._closing:
            return False
        
        retval = False
        if self._channel:
            # NOTE: ProtoBuf messages need to be converted first.
            body = bytes(body.SerializeToString())
            self._channel.basic_publish(
                self._options.exchange, 
                self._options.routing_key_out, 
                body=body)
            retval = True
        return retval
            
    
    def acknowledge_message(self, delivery_tag):
        self._channel.basic_ack(delivery_tag)
        self._log.info("Message acknowledged")
    
    def stop_consuming(self):
        self._log.info("Stopping consumption")
        if self._channel:
            self._channel.basic_cancel(self.on_cancelok, self._consumer_tag)
    
    def start_consuming(self):
        self._log.info("Starting consumption of channel")
        self.add_on_cancel_callback()
        self._consumer_tag = self._channel.basic_consume(self.on_message)
    
    def close_channel(self):
        self._log.info("Closing channel")
        if self._channel:
            self._channel.close()
    
    def open_channel(self):
        self._log.info("Opening channel")
        self._connection.channel(on_open_callback=self.on_channel_open)
    
    def start_bridge(self):
        try:
            self._log.info("Starting AMQP bridge")
            self._connection = self.connect()
            self._connection.ioloop.start()
        except Exception as e:
            self._log.warning('Failed to start bridge: {0}'.format(e.args))
        
    def stop_bridge(self):
        self._log.info("Stopping AMQP bridge")
        self._closing = True
        try:
            self.stop_consuming()
            if self._connection:
                self._connection.ioloop.start() # Not a typo
        except Exception as e:
            pass
    
    def add_on_connection_close_callback(self):
        self._connection.add_on_close_callback(self.on_connection_closed)
    
    def add_on_channel_close_callback(self):
        self._channel.add_on_close_callback(self.on_channel_closed)
    
    def add_on_cancel_callback(self):
        self._channel.add_on_cancel_callback(self.on_consumer_cancelled)
    
    """
    Callbacks
    """
    
    def on_connection_closed(self, connection, reply_code, reply_text):
        self._channel = None
        if self._closing:
            if self._connection:
                self._connection.ioloop.stop()
            self._connection = None
            self._log.info("Connection closed")
        else:
            if self._connection:
                self._connection.add_timeout(5, self.reconnect)
    
    def on_connection_open(self, unused_connection):
        self._log.info("Connection opened")
        self.add_on_connection_close_callback()
        self.open_channel()
    
    """
    Keep a handle to the channel
    Add the closing callback
    Setup the exchange
    Enable delivery confirmations (for publishing)
    Push status via properties.
    """
    def on_channel_open(self, channel):
        self._channel = channel
        self._log.info("Channel opened")
        self.add_on_channel_close_callback()
        self.setup_exchange(self._options.exchange)
        self.enable_delivery_confirmations()
    
    def on_channel_closed(self, channel, reply_code, reply_text):
        self._log.info("Channel closed")
        if self._closing and self._connection:
            self._connection.close()
    
    def on_exchange_declareok(self, unused_frame):
        self._log.info("Exchange OK")
        self.setup_queue()
    
    def on_queue_declareok(self, method_frame):
        self._log.info("Queue OK")
        self._channel.queue_bind(self.on_bindok, 
            "",
            exchange=self._options.exchange, 
            routing_key=self._options.routing_key_in)
    
    def on_delivery_confirmation(self, method_frame):
        self._log.info("Message acknowledged at server.")
    
    def on_consumer_cancelled(self, method_frame):
        self._log.info("Consumer Cancelled; Closing...")
        if self._channel:
            self._channel.close()
            
    def on_message(self, unused_channel, basic_deliver, properties, body):
        self._log.info("Message received")
        self.acknowledge_message(basic_deliver.delivery_tag)
        if type(body) == unicode:
            data = bytearray(body, "utf-8")
            body = bytes(data)
            
        try:
            message = PBConversationStart_pb2.PBConversationStartMessage()
            message.MergeFromString(body)
            
            if message.conversation in self._conversations:
                if not self._conversations[message.conversation].start():
                    self._log.warning("Conversation '{0}' already running.".format(message.conversation))
            else:
                reply = PBConversationStatus_pb2.PBConversationStatusMessage()
                reply.conversation = message.conversation
                reply.status = PBConversationStatus_pb2.FAILED
                reply.message = "Conversation not found."
                self.publish_message(reply)
                self.lariat_downlink.info = "Conversation not found: {0}".format(message.conversation)
                
        except Exception as e:
            self._log.warning("Exception occurred when receiving message: {0}".format(e.args))
        
        
    def on_cancelok(self, unused_frame):
        self.close_channel()
        
    def on_bindok(self, unused_frame):
        self.start_consuming()
        
if __name__=="__main__":
    gw = RH_Gateway()
    
    options = AMQPConnectionOptions()
    options.exchange = "redhawk_exchange"
    options.exchange_type = "topic"
    options.routing_key_out = "bridge"
    options.routing_key_in = "redhawk"
    # TODO ??
