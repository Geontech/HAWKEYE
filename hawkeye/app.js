/*
 * 
    Copyright: 2014 Geon Technologies, LLC
    
    This program is free software: you can redistribute it and/or modify
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
 * @description
 *    HAWKEYE Control Panel Server uses Node.js as its backend server and 
 *    a handful of open-source libraries including Socket.io and ZeroRPC
 *    to serve a user's Control Panel design as a web site to a compatible
 *    browser.
 * 
 *   NOTE: "app" is exported to make it available to implementers of this server.
 */

// NOTE: These are the available options for the rh_cp_server.
var DEFAULTS = { UserPort : 8888, 
                 Log_STDOUT : false,
                 Log_STDERR : false  };

module.exports = function (app, options) {

    var url = require('url'),
        fs = require('fs'),
        rh_session = require('./util/rh_session'),
        express = require('express'),
        server = require('http').createServer(app),
        sio = require('socket.io').listen(server);
    
    var settings = DEFAULTS;
    if (typeof options !== "undefined") {
        for (key in DEFAULTS) {
            if (options.hasOwnProperty(key)) {
                console.log("Default modified: " + key + "->" + options[key]);
                settings[key] = options[key];
            }
        }
    }
    
    // Merge user site and the base.
    app.use(express.static(__dirname + "/site"));
    
    // Special Process-related events
    // If SIGINT, clean up all children.
    process.on('exit', function() {
        console.info("Server exiting...");
    });
    process.on('SIGINT', function() { 
        rh_session.removeAllSessions(); 
        setTimeout(process.exit, 100, 0);
    });
    process.on('SIGTERM', function() { 
        rh_session.removeAllSessions(); 
        setTimeout(process.exit, 100, 0);
    });
    process.on('uncaughtException', function(ex) { 
        console.error(ex.stack);
        process.exit(1);
    });
        
    // ************ MANAGE SOCKET.IO MESSAGES ******* //
    // When the browser's JS reaches out, the real work starts.
    // See "Server" @ https://github.com/LearnBoost/socket.io/wiki/Exposed-events
    // The "sockets" member only has one named event: connection.
    // FIXME: What to do when client is reconnecting/refreshing?  Seems to cause ZeroRPC
    //        and child process artifacts in rh_session occasionally (i.e., rh_gateway.py
    //        instances sleeping in the background for all TIME ... Time... time...)
    sio.sockets.on('connection', function(socket) {
        console.info('Establishing client session: ' + socket.id);      
        session = rh_session.getSessionForSocket(socket);
        if (settings.Log_STDERR) {
            session.mapSTDERRtoFunction( function(data) {
                console.info('RH Gateway stderr: ' + data);
            });
        }        
        if (settings.Log_STDOUT) {
            session.mapSTDOUTtoFunction( function(data) {
                console.info('RH Gateway stdout: ' + data);
            });
        }
    });
    
    // TODO: Make this a setting.
    sio.set('log level', 1); // Reduce log messages. For bulkio, you'll thank me.
    server.listen(settings.UserPort);
    console.log("HAWKEYE Control Panel Server Started");
};


