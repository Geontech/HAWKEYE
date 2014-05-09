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
 * @description
 *   This example adds a custom message handler, template, and CSS.  The result
 *   is two main panels, one displaying a list of domains and waveforms; the other 
 *   the selected domain's Device Manager hierarchy.
 */

var express = require('express'),
    app = express();

// Set the site root so rhcp can merge.
app.use(express.static(__dirname + '/site'));
var rhcp = require('../../hawkeye')(app);