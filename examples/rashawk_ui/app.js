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

 * @author:  Thomas Goodwin and Joe Reinhart
 * 
 * @description:
 *   This example was made to support our APG Tech Challenge efforts.
 *   In the challenge, a group of Raspberry Pis have access to an RTL
 *   dongle, WiFi, and GPS making them capable of streaming a wide 
 *   range of frequencies and position information back to a remotely
 *   executing Waveform.  This UI will support that effort by integrating
 *   the GPS information with Google Maps.
 */

var express = require('express'),
    app = express();

// Set the site root    
app.use(express.static(__dirname + '/site'));

// Create the RHCP and allow it to merge.
var opts = undefined;
/*
opts = { Log_STDERR: true, 
         Log_STDOUT: true  };
/* Use the above for debugging */
var rhcp = require('../../hawkeye')(app, opts);

