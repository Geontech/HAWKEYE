/**
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
 * @description
 *   Simplest possible example - create a server using default settings and site files.
 *   Result is a hierarchical menu of the running domain with some other functionality
 *   such as being able to stream from ports and change properties.
 */
var express = require('express'),
    app = express();
    
var rhui = require('../../hawkeye')(app);