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
 *   This is a simple example for how to override the message handling and 
 *   parent container ID checks handled in the rh_cp_client.  
 * 
 *   Overriding the message handlers allows you to customize the HTML going 
 *   into the rhtype_container for the particular message.
 * 
 *   Overriding the parent ID will determine into which user-defined "parent" 
 *   ID in which to place the particular rhtype_container.
 * 
 *   THIS EXAMPLE:
 * 
 *   Ignore all `domain` messages and instead collect _all_ applications 
 *   and device managers across all domains into two new sub-panels.
 */

/* 
 * @description
 *   Custom RH_Message handlers for creating special control panels.  
 *   The keys are:
 *     1) messageHandlers is an associative array using rhtype
 *     2) the function must accept a msg and return either:
 *        a) A single DOM Element
 *        b) An array of DOM Elements
 *        c) null (to ignore the message entirely)
 * 
 * @notes
 *   Some helpful links for creating elements:
 * 
 *    - Create or get document DOM Elements
 *      http://www.w3schools.com/jsref/dom_obj_document.asp
 * 
 *    - Modify those DOM Elements
 *      http://www.w3schools.com/jsref/dom_obj_all.asp
 */

jQuery.noConflict();
(function($) {
    messageHandlers = {
        domain : function(message) {
            /* 
             * Augmented behavior: Drop all domain_container objects.
             */
           return null;
        },
        device_manager: function(message) {
            /*
             * Augmented behavior: add a refresh button.
             */
            var $obj = $('<div>').device_manager_container({message: message});
            var $refresh = $('<input type="button">')
                        .addClass('refresh')
                        .attr('value', 'Refresh')
                        .attr('onclick', getActionString(message, 'update', true))
                        .insertAfter($obj.children('.show_hide'));
            
            return $obj;
        }
    };
})(jQuery);

/*
 * @description
 *   This structure is an associative array combining RH_Message rhtypes 
 *   vs. alternate IDs to use as parents for those rhtypes.  Every message
 *   still results in a container of rhtype_class with ID equal to its rhid,
 *   but the container in which that rhtype_class is inserted will change.
 *   
 *   For example, the default container ID for each child is its parent's
 *   ID in the overall REDHAWK hierarchy.  A Device's parent is always its
 *   Device Manager, and that Device Manager's parent is always the Domain.
 *   The Domain's parent ID is always 'hawkeye_ui'.  In the override below,
 *   all device_manager containers will be inserted into a panel whose ID
 *   matches redhawk_device_managers (see example_custom.html).  The result
 *   will be a Domain listing in the 'hawkeye_ui' and its device managers
 *   (and their children, etc.) in a separate panel.
 */
parentIDOverrides = {
    device_manager : 'redhawk_device_managers',
    application    : 'redhawk_applications'
};
