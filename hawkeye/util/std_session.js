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
 *    to the server-side REDHAWK Python model STDIN and STDOUT in the RH Gateway subprocess.  
 *    The flow of data is:
 * 
 *       Client's Browser with Socket.io Client
 *       RH Session Socket.io Server
 *       Node.js Server
 *       Subproces STDIN/OUT to RH Gateway
 *       REDHAWK Python Model 
 */

var sio = require('socket.io'),
    url = require('url'),
    path = require('path'),
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
        if (sessions[i].sessionID() == socket.id) {
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
    var socket = socketIn;
    
    // Spawn and configure RH Gateway child process.
    var p = path.relative(process.cwd(), __dirname);
    var gateway = spawn(
        'python', [ p + '/std_front.py'], // Python, STDIN/OUT frontend to  RH Gateway
        { stdio:['pipe', 'pipe', process.stderr] });   // Configure STDIN/OUT as pipes to this process
    gateway
        .on('close', function (code, signal) {
            console.log("Closed Node<-REDHAWK Client w/ code: " + code);
        })
        .stdout.on('data', function (data) {
            // Handle output
            if ("\n" != data) {
                socket.send(data);
            }
        });
    
    // (EXTERNAL) Logging text
    this.name = "RH Session ID " + socket.id;
    
    // Socket.io Instance for managing browser interface to the RH_Session
    // See "Server" @ https://github.com/LearnBoost/socket.io/wiki/Exposed-events
    // TODO: Add ability for the server to pass different callbacks to these.
    socket
        .on('message', function(msg, ackCallback) {
            gateway.stdin.write(msg + '\n');
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
    
    // Expose the socket ID as the session ID.
    this.sessionID = function() {
        return socket.id;
    };
    
    // Shutdown by ending stdin.
    this.shutdown = function(callback) {
        try {
            console.log("Closing Node<-REDHAWK Client");
            gateway.stdin.end();
            //gateway.kill('SIGINT');
        }
        catch (error) {
            console.error("Error on shutdown of session"); console.error(error);
        }
        finally {
            if (callback) callback();
        }
            
    };
    
    // Mapping STDERR and STDOUT of the underlying process
    this.mapSTDERRtoFunction = function(fn) { /* gateway.stderr.on('data', fn); */ };
    this.mapSTDOUTtoFunction = function(fn) { /* gateway.stdout.on('data', fn); */ };
    
    // TODO: Add ability to change message, anything, and disconnect callback functions.
    console.log("RH Session Created.");
}
