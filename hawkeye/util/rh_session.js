/**
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

 * @author Thomas Goodwin
 * 
 * Description:
 *    Each REDHAWK Session (i.e., socket.io session) provides client-specific access
 *    to the server-side REDHAWK Python model using ZeroRPC.  The flow of data is:
 * 
 *       Client's Browser with Socket.io Client
 *       RH Session Socket.io Server
 *       Node.js Server
 *       RH Session ZeroRPC Client and Server
 *       RH Gateway ZeroRPC Client and Server
 *       REDHAWK Python Model 
 */
// TODO: Investigate if it would be better to directly connect the RH Gateway
//       to the client using ZeroRPC rather than using socket.io for one leg 
//       of the trip. 


var sio = require('socket.io'),
    url = require('url'),
    path = require('path'),
    zerorpc = require('zerorpc'),
    spawn = require('child_process').spawn,
    RH_Message = require('../site/js/rh_message');

// Local list of active or idle sessions
var sessions = [];

/* ******************************************
 * Public interface methods
 * ******************************************/

module.exports = {
    getSessionForSocket : getSessionForSocket,
    removeSessionForSocket : removeSessionForSocket,
    removeAllSessions : removeAllSessions,
    RH_Session : RH_Session
};

// Get or return new session based on socket
// throwIfNotFound is optional and defaults to false.
function getSessionForSocket (socket, throwIfNotFound) {
    throwIfNotFound = (typeof throwIfNotFound === "undefined") ? false : throwIfNotFound;
    
    var len = sessions.length;
    for (var i = 0; i < len; i++) {
        if (sessions[i].sessionID() === socket.id) {
            return sessions[i];
        }
    }
    if (throwIfNotFound === true) throw 'No session found for socket.';
        
    // Not found and no throw, create and return a new one.
    session = new RH_Session(socket);
    sessions.push(session);
    return session;
};
    
// Finds the session for the socket, shuts it down, and removes it.
function removeSessionForSocket (socket, callback) {
    try {
        session = getSessionForSocket(socket, true);
        session.shutdown(); 
        
        var remove_idx = -1;
        var len = sessions.length;
        for (var i = 0; i < len; i++) {
            if (session === sessions[i]) {
                remove_idx = i;
                break;
            }
        }        
        if (0 <= remove_idx) sessions.splice(remove_idx, 1);
    }
    catch (error) {
        console.error("Failed to remove session; see error. ");
        console.error(error);
    }
    finally {
        if (callback) callback();
    }
    
};
    
// Shutdown and remove all sessions
function removeAllSessions (callback) {
    var len = sessions.length;
    for (var i = 0; i < len; i++) {
        try {
            sessions[i].shutdown();
        }
        catch (error) {
            console.error("Error when shutting down :" + sessions[i].sessionID());
        }
    }
    sessions.length = 0; // Clear the array.
    if (callback) callback();
};

// RH_Session class is public along with a few methods below.
// It represents the three sockets exchanging data between
// REHDAWK and the Client's browser.
// Use the session's invoke() method to call named functions on
// the REDHAWK Gateway.
function RH_Session (socketIn) {    
    // ZeroRPC client and server will have a .sock UNIX Socket
    //    Node.js server side: _node2rh
    //    REDHAWK server side: _rh2node
    var socket = socketIn;
    var p = path.relative(process.cwd(), __dirname);
    var addr = 'ipc://' + p + '/zpcsockets/' + String(socket.id) + '.sock';
    var gateway = spawn('python', [p + '/rh_gateway/rh_gateway.py', addr]);
    
    var client = new zerorpc.Client();
    client.connect(addr + '_rh2node');
    
    // Logging text
    this.name = "RH Session ID " + socket.id;
    
    
    // Socket.io Instance for managing browser interface to the RH_Session
    // See "Server" @ https://github.com/LearnBoost/socket.io/wiki/Exposed-events
    // TODO: Add ability for the server to pass different callbacks to these.
    socket
        .on('message', function(msg, ackCallback) {
            client.invoke("passMessages", JSON.parse(msg), function(error, response, more) {
                if (error) {
                    console.error("RH_Session failed to pass message to RH_Gateway:");
                    console.error(error);
                }
                else if (null != response) {
                    socket.send(JSON.stringify(response));
                }
            });
        })
        .on('anything', function(data) {
            // TODO: This is any other event other than message or disconnect.
            //console.info("Client sent 'anything' to RH_Session: " + data);
        })
        .on('disconnect', function() {
            console.info("Removing RH_Session for disconnected socket: " + socket.id);
            removeSessionForSocket(socket);
        })
        .on('error', function() {
            console.error("Socket " + socket.id + " had an error.  Closing RH_Session.");
            removeSessionForSocket(socket);
        });

    
    // ZeroRPC Instance for handling RH_Gateway event callbacks
    // TODO: Define more callbacks??  Do more processing in Node?
    //
    // NOTE: ALL CALLBACKS DEFINED HERE must have the _last_ argument
    //       be a function reply which MUST be called or else it will stall
    //       the client invocation on the python side.
    var server = new zerorpc.Server({
        // Converts and forwards messages to socket.io client. 
        passMessages: function(data, reply) {
            try {
                //console.log("RH_Gateway passed " + data.length + " messages to the client.");
                data = JSON.stringify(data);
                socket.send(data);
                reply(true);
            }
            catch (error) {
                console.log("Error occurred when passing message to client:");
                console.log(data);
                console.log(error);
                reply(false);
            }
        }
    });
    server.bind(addr + '_node2rh');
    
    // When gateway goes down, close the server.
    gateway.on('exit', function (code, signal) {
        console.log("Closed Node<-REDHAWK Client w/ code: " + code);
    });
    
    // Expose the socket ID as the session ID.
    this.sessionID = function() {
        return socket.id;
    };
    
    // Shutdown the ZeroRPC connections and terminate it.
    this.shutdown = function(callback) {
        try {
            console.log("Closing Node->REDHAWK Server");
            server.close();
            
            console.log("Closing Node<-REDHAWK Client");
            gateway.kill();
        }
        catch (error) {
            console.error("Error on shutdown of session"); console.error(error);
        }
        finally {
            if (callback) callback();
        }
            
    };
    
    // Mapping STDERR and STDOUT of the underlying process
    this.mapSTDERRtoFunction = function(fn) { gateway.stderr.on('data', fn); };
    this.mapSTDOUTtoFunction = function(fn) { gateway.stdout.on('data', fn); };
    
    // TODO: Add ability to change message, anything, and disconnect callback functions.
    console.log("RH Session Created.");
}
