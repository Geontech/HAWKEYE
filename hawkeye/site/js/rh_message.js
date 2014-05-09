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
 * @description 
 * Message prototype for exchanges between browser and session
 * @param change - '', 'add', 'remove', 'update'
 * @param rhtype - 'domain', 'device_manager', 'device', 'service', 
 *                 'application', 'component', 'port', 'property', ''
 * @param rhid - a unique ID for rhtype in question
 * @param more - an associative array of any additional data pertaining to 
 *               this message.  It should always include a `parentID` key
 *               corresponding to the rhid's parent's rhid or be empty.
 *
 * Startup example
 *          Client Sends           Client Receives an array of:
 *      { change: 'add',         []{ change: 'add',
 *        rhtype: 'domain',         rhtype:  'domain', 
 *        rhid:   '',               rhid:    'domain id',
 *        rhname: '',               rhname:  'domain name',
 *        more: {} }                more:    {} }, ... , {}]
*/
function RH_Message(change, rhtype, rhid, rhname, more) {
    this.change = (typeof change === "undefined") ? '' : change;
    this.rhtype = (typeof rhtype === "undefined") ? '' : rhtype;
    this.rhid =   (typeof rhid   === "undefined") ? '' : rhid;
    this.rhname = (typeof rhname === "undefined") ? '' : rhname;
    this.more =   (typeof more   === "undefined") ? new Object() : more;
    
    if (typeof this.more.parentID === "undefined") {
        this.more.parentID = '';
    }
}

/* Takes a string `id` and escapes : and . with \\.
 * prevent collisions in jQuery selections.
 */
function cleanRHID(rhid) {
    var clean = rhid.replace(/:/g, "\\:").replace(/\./g, "\\.");
    return clean;
}

/* Takes a string `id` and swaps :, ., and - for _ so IDS can be
 * used as keys in JavaScript hash maps/associative arrays.
 */
function keyifyRHID(rhid) {
    var clean = rhid.replace(/:/g, "_")
                    .replace(/\./g, "_")
                    .replace(/-/g, "_");
    return clean;
}
    
/*
 * Strips an RH Message's `more` field to only the ParentID.
 * @param message The message to reference
 * @param copy Whether or not to copy the message first.
 */
function stripMessage(message) {
    var temp = new RH_Message(message.change, message.rhtype, message.rhid, 
            message.rhname);
    temp.more.parentID = message.more.parentID;
    return temp;
}
