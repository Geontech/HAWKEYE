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
    
    HAWKEYE Control Panel Client-side JavaScript
    
 * @author Thomas Goodwin
 *  * 
 * @description
 *   This script contains the initial callbacks and utility methods for message
 *   processing into HTML tags.  The purpose is to let the user include a message 
 *   handler script consisting of an associative array of functions using the 
 *   RH_Message.rhtype as its key. 
 *
 *   EXAMPLE: messageHandlers
 *    
 *      messageHandlers = {
 *         // Method treats all domain objects the same.
 *         domain : function(msg, previous) {
 *            // Inserts a radio button, perhaps, or some other elements
 *            return domaincontnetsobj;
 *         },
 *      
 *         device : function(msg, previous) {
 *             if (msg.rhname == 'my_special_device') {
 *                // returns some fancy set of tags to represent this device
 *                return specialobjs;
 *             }
 *             else {
 *                // returns null to drop all other devices from being displayed.
 *                return null;
 *             }
 *         }
 *      };
 * 
 *    
 *   IMPORTANT: The functions in this array will be passed an RH_Message and the previous
 *   parent container, if it existed.  The function must return either a DOM Element, array
 *   of DOM Elements, or null.  If returning a DOM Element, it will be placed in a <div>
 *   whose class is 'rhtype_container' and id is 'rhid'.  If the message change is a `stream`
 *   the handler should update `previous` since no DOM elements are going to get swapped from
 *   the view.
 * 
 * 
 *   EXAMPLE: parentIDOverrides
 * 
 *      parentIDOverrides = {
 *         device  : 'rh_devices',
 *         service : 'rh_services' 
 *      };
 * 
 *   Assuming that within the HTML document, exactly 1 container will 
 *   have the ID rh_devices, and exactly one will have rh_services.
 *     
 *   These custom elements can be added to the server's Path_MessageHandlers setting.  
 * 
 *   NOTE: Any attributed file in that path setting is appended to the END of this script.
 */

/* Wrapping our HAWKEYE Widgets and implementation to avoid future library conflicts */
var socket = io.connect();
jQuery.noConflict();
(function($) {    
    // Setup Socket.io when the document is ready.
    $( document ).ready( function() {
        socket.on('connect', function () {
            // Handle startup?
        });
        socket.on('error', function(data) {
            alert('Failed to connect to gateway.');
            socket.disconnect();
        });
        socket.on('message', processMessages);
    });
    
    
    function processMessages(messages) {
        messages = JSON.parse(messages);
        messages.forEach( function(message) {
            try {
                switch (message.change) {
                    case 'add':
                        // Attempt a query.  
                        //   If found: skip the message.  
                        //   Else: attempt process it.
                        var $awidget = $("#" + cleanRHID(message.rhid));
                        if (0 == $awidget.length) {
                            $awidget = getNewWidgetForMessage(message);
                            if (null != $awidget) {
                                var $parent = getParentFromMessage(message);
                                $awidget.appendTo($parent);
                                
                                // Set hide/show relative to siblings if they exist.  If none exists,
                                // hide the new widget, initially.
                                var $sibs = $parent.siblings('div');
                                if ($sibs.length) {
                                    if ($sibs.eq(0).is(':visible')) {
                                        $awidget.show('fast');
                                    }
                                    else {
                                        $awidget.hide('fast');
                                    }
                                }
                            }
                        }
                        break;
                    case 'remove':
                        // Find and animate the removal of the element by its ID if found.
                        var $widget = $("#" + cleanRHID(message.rhid));
                        if ($widget.length) {
                            // Let the widget process the last message as it's being removed.
                            $widget.data("hawkeye-" + message.rhtype + "_container")
                                      .configureMessage(message);
                            $widget.hide('fast', function () {$widget.remove();});
                        }
                        break;
                    case 'update':
                    case 'stream':
                        var $theWidget = $("#" + cleanRHID(message.rhid));
                        if ($theWidget.length)
                            $theWidget.data("hawkeye-" + message.rhtype + "_container")
                                      .configureMessage(message);
                        break;
                    default:
                        console.error("Unknown change type: " + message.change);
                }
            }
            catch (error) {
                console.error("ERROR: processing message" + JSON.stringify(message));
                console.error("Stack:" + error.stack);
                console.error(error);
                return false;
            }
        });
        return true;
    };
    
    /*
     * Get the jQuery representing this message, if necessary.  The user's messageHandlers
     * associative array is given precedence over the defaults.  If the user's messageHandler
     * fails (exceptions) no content will be created.
     * 
     * The UI Widget must be a subclass default_msg_container to support the _configureMessage
     * method.
     *  
     * @param message The RH_Message to be processed
     * @return jQuery UI Widget or null.
     */
    function getNewWidgetForMessage (message) {
        var $widget = null;
        
        if ((typeof messageHandlers !== "undefined") && (message.rhtype in messageHandlers)) {
            try {
                $widget = messageHandlers[message.rhtype](message);
            }
            catch (error) {
                console.error("User's message handler failed for rhtype: " + message.rhtype);
                console.error(error.stack);
                console.error(error);
                $widget = null;
            }
        }
        else {
            $widget = $('<div>').hide();
            switch (message.rhtype) {
                case 'domain':
                    $widget.domain_container({message: message})
                           .show();
                    break;
                case 'device':
                    $widget.device_container({message: message});
                    break;
                case 'component':
                    $widget.component_container({message: message});
                    break;
                case 'port':
                    $widget.port_container({message: message});
                    break;
                case 'property':
                    $widget.property_container({message: message});
                    break;
                case 'application':
                    $widget.application_container({message: message});
                    break;
                case 'device_manager':
                    $widget.device_manager_container({message: message});
                    break;
                case 'service':
                    $widget.service_container({message: message});
                    break;
                default:
                    console.warning("Unknown type being processed: " + message.rhtype);
                    $widget = null;
            }
        }
        // Assign ID if widget is valid.
        if (null != $widget) {
            $widget.attr({id: message.rhid});
        }
        return $widget;
    }
    
    /* Attempt to get the parent document object based on the following 
     * search order:
     *   1) parentIDOverrides 
     *   2) msg.more.parentID
     *      a) If container with class `rhtype_group` is found in parent, 
     *         use it as parent.
     *      b) Else, use parent.
     *   3) alternate
     * 
     * @param message The RH_Message which may contain more.parentID as a parent ID.
     * @return $parent jQuery UI Widget to append a child to.
     */
    function getParentFromMessage(message) {
        var $parent = [];
        var id = '';

        if ((typeof parentIDOverrides !== "undefined") && (message.rhtype in parentIDOverrides)) {
            $parent = $("#" + parentIDOverrides[message.rhtype]);
        }
        else if ((typeof message.more.parentID !== "undefined") && ('' != message.more.parentID)) {
            // Search for an rhtype_group classed child;
            var ps = "#" + cleanRHID(message.more.parentID);
            var gs = "div."+ message.rhtype + "_group";
            id = ps + " " + gs;
            $parent = $(id); // Like CSS: #id div.class_group
            
            if (0 == $parent.length) {
                // Failed, try the parent.
                $parent = $(ps);
                id = '';
            } 
        }
        
        if (0 == $parent.length) {
            // Still nothing...use the default
            $parent = $defaultParent();
        }
        $parent = $parent.eq(0);
        
        if ('' == id)
            id = $parent.attr('id');
        
        // console.log("Parent container found at ID: " + id);
        return $parent;
    }
    
    var $defaultParent = function () {
        return $("#hawkeye_ui");
    };
    
    
    /* COMMON ANIMATION/BEHAVIORS */    
    /* All show_hide label tags will toggle subsequent siblings for hide/show. */
    function toggleSiblings (obj, selector) {
        var $sibs = $(obj).siblings(selector);
        if ($sibs.eq(0).is(":visible")) {
            $sibs.hide('fast');
        }
        else {
            $sibs.show('fast');
        }
    };
    $(document)
        .on('click', 'label.show_hide', function () {
            toggleSiblings(this, 'div');
        })
        .on('click', 'label.rh_prop_label', function () {
            toggleSiblings(this, 'ol');
            toggleSiblings(this, 'ul');
        });
    
   
   
    
    /* jQuery Widget and Plugin interface.  Our namespace is "hawkeye" */
   
   
   
    /*
     * Default container is simply a container whose class is `type_container`
     * and top label of class `show_hide` whose text is `labelText`.  
     * 
     * Clicking the span will hide or show all div siblings.
     */
    $.widget("hawkeye.default_container", {
        options: {
            type: 'default',
            labelText: 'Default'
        },
        _create: function() {
            this.$label = $('<label>').addClass('show_hide');
            this.element.append(this.$label);
            this._update();
        },
        _setOption: function (key, value) {
            this.options[key] = value;
            this._update();
        },
        _usingClassName: function() {
            return this.options.type + "_container";
        },
        _update: function () {
            this.element.removeClass();
            this.element.addClass(this._usingClassName());
            this.$label.text(this.options.labelText);
        }
    });
    
    
    /*
     * Inherits from default_container and results in a class of
     * `name_group` with the same labelText and toggling behavior
     * as before.
     */
    $.widget("hawkeye.default_group", $.hawkeye.default_container, {
        _usingClassName: function () {
            return this.options.type + "_group";
        }
    });
    
    /* 
     * The options for type and labelText no longer matter if message (RH_Message)
     * is supplied -- it overrides each with rhtype and rhname, respectively.
     * 
     * Events: Raises 'configured' when configureMessage successfully sets
     * the message.  Function sig is: function (event, data){} where data is the
     * RH_Message that was configured.
     */
    $.widget("hawkeye.default_msg_container", $.hawkeye.default_container, {
        options: {
            message: null,
            // Event callback holder.
            configured: $.noop
        },
        _create: function () {
            this._super(); // calls update.
            this.configureMessage(this.options.message);
        },
        _setOption: function (key, value) {
            if ('message' == key) {
                this.configureMessage(value);
            }
        },
        // Children should extend this call.
        configureMessage: function (newMessage) {
            if (null != newMessage) {
                this.options.message = newMessage;
                this.options.type = this.options.message.rhtype;
                this.options.labelText = this.options.message.rhname;
                this._update();
                this._trigger('configured', null, newMessage);
            }
        }
    });
    
    /* 
     * Domain container adds 2 subgroups for device_manager and 
     * application containers.
     */
    $.widget("hawkeye.domain_container", $.hawkeye.default_msg_container, {
        _create: function() {
            this._super();
            this.element.append(
                $('<div>').default_group({ 
                    type: 'device_manager', 
                    labelText: 'Device Managers'}).hide(),
                $('<div>').default_group({
                    type: 'application', 
                    labelText: 'Running Applications'}).hide()
                );
        }
    });
    
    /* Stand-ins for user-overrides and the update/stream mechanic. */
    $.widget("hawkeye.device_manager_container", $.hawkeye.default_msg_container, {});
    $.widget("hawkeye.service_container", $.hawkeye.default_msg_container, {});
    $.widget("hawkeye.application_container", $.hawkeye.default_msg_container, {
        _create: function() {
            this.$startstop = $('<input>')
                .attr('type', 'button')
                .addClass('rh_app_control');
            this.$release = $('<input>')
                .attr('type', 'button')
                .attr('value', 'Release')
                .addClass('rh_app_control')
                .click($.proxy(this._release, this));
            this._super();
            this.element.append(this.$startstop)
                        .append(this.$release);
        },
        configureMessage: function (newMessage) {
            if (true == newMessage.more.running) {
                this.$startstop
                    .attr('value', 'Stop')
                    .click($.proxy(this._stop, this));
            }
            else {
                this.$startstop
                    .attr('value', 'Start')
                    .click($.proxy(this._start, this));
            }
            this._super(newMessage);
        },
        _stop: function() {
            // Send stop message.
            var msg = stripMessage(this.options.message);
            msg.change = 'stop';
            request(msg);
        },
        _start: function() {
            // Send a start message.
            var msg = stripMessage(this.options.message);
            msg.change = 'start';
            request(msg);
        },
        _release: function () {
            // Double stop releases the application.
            this._stop();
            this._stop();
        }
        
        
    });
    
    /*
     * Devices and Components are basically identical with 2 groups:
     *   1) Properties
     *   2) Ports
     */
    $.widget("hawkeye.component_container", $.hawkeye.default_msg_container, {
        _create: function () {
            this._super();
            this.element.append(
                $('<div>').default_group({
                    type:      'property',
                    labelText: 'Properties'}).hide(),
                $('<div>').default_group({
                    type:      'port' ,
                    labelText: 'Ports'}).hide()
                );
        }
    });
    $.widget("hawkeye.device_container", $.hawkeye.component_container, {});
    
    /*
     * Simple data row to go into a data table.
     */
    $.widget("hawkeye.data_row", {
        options: {
            num_columns: 1
        },
        _create: function () {
            for (var i = 0; i < this.options.num_columns; i++) {
                this.element.append($('<td>'));
            }
        },
        getColumn: function (column) {
            return this.element.children('td').eq(column);
        }
    });
    /* 
     * Simple TABLE widget with rows and columns as options
     */
    $.widget("hawkeye.data_table", {
        options: {
            num_columns: 1,
            num_rows: 1
        },
        _create: function () {
            for (var r = 0; r < this.options.num_rows; r++) {
                this.element.append($('<tr>').data_row({num_columns: this.options.num_columns}));
            }
        },
        getCell: function (row, column) {
            return this.element.find('tr').eq(row).data('hawkeye-data_row').getColumn(column);
        },
        getCellValue: function (row, column) {
            return this.getCell(row, column).html();
        },
        setCellValue: function (row, column, html) {
            var $cell = this.getCell(row, column);
            this.getCell(row, column).html(html);
        }
    });
    
    /*
     * Port container adds stats table and start/stop button behavior.
     */
    $.widget("hawkeye.port_container", $.hawkeye.default_msg_container, {
        _create: function () {
            this.$table = $('<table>').data_table({num_columns: 2, num_rows: 2})
                                      .addClass('port_statistics')
                                      .hide();
            this.$table.data_table("setCellValue", 0, 0, "Packet Count")
                       .data_table("setCellValue", 1, 0, "Length");
            
            this.$startstop = $("<input>")
                .attr('type', 'button')
                .addClass('start_stop');
                
            this._super();
            
            this.element.append(this.$startstop);
            this.element.append(this.$table);
        },
        configureMessage: function (newMessage) {
            if (('update' == newMessage.change) || 
                ('add'    == newMessage.change)){
                // // // 
                // Clear stats
                this.$table.data_table("setCellValue", 0, 1, 0)
                           .data_table("setCellValue", 1, 1, 0)
                           .hide('fast');
                
                // Set button text to Start if not already done so.
                if ('Start' != this.$startstop.attr('value')) {
                    this.$startstop
                        .attr('value', 'Start')
                        .attr('onclick', getActionString(newMessage, 'start', true));
                }   
            }
            else if ('stream' == newMessage.change) {
                if ('Stop' != this.$startstop.attr('value')) {
                    this.$startstop
                        .attr('value', 'Stop')
                        .attr('onclick', getActionString(newMessage, 'stop', true));
                }
                
                if (0 < newMessage.more.data.length) {
                    var count = parseInt(this.$table.data('hawkeye-data_table').getCellValue(0, 1));
                    count++;
                    this.$table.data_table("setCellValue", 0, 1, count)
                               .data_table("setCellValue", 1, 1, newMessage.more.data.length)
                               .show('fast');
                }
            }
            this._super(newMessage);
        }
    });
    
    /*
     * Property container builds an unordered and ordered lists as 
     * deep as necessary to hold all properties.  If the Property
     * is an array, the resulting list is ordered.  If not, it's 
     * an unordered list.  If the property is editable, a `set` 
     * button is available.     
     * 
     * The message.more format has value and access.  Access 
     * applies to anything in the value.  The value could be
     * any of the possible REDHAWK Hierarchy options.  Only
     * one Property Container is created per structure.
     * 
     * Each <input type='text'> added will have class property_value
     * and attributes: index and name.
     */
    /* REDHAWK Hierarchy options:
     *    Simple
     *    Structure
     *       <simple a>
     *       <simple b>
     *          ...
     *    Simple Array
     *       <simple A 1>
     *       <simple A 2>
     *          ...
     *    Structure Array
     *       <struct AA 1>
     *          <simple a>
     *          <simple b>
     *             ...
     *       <struct AA 2> 
     *          <simple a>
     *          <simple b>
     *             ...
     *          ...
     */
    $.widget("hawkeye.property_container", $.hawkeye.default_msg_container, {
        _create: function () {
            this.$form = $('<form>');
            this._super();
            this.element.append(this.$form);
            this.$label
                .removeClass("show_hide")
                .addClass("rh_prop_label");
        },
        // Function does not modify the model.  Returns only a list object.
        _createListItem: function(name, value, rhidx, readonly) {
            var $item = this._createInputField(name, value, readonly);
            $item.attr('rhidx', rhidx);
            
            var $li = $('<li>')
                .append($('<label>')        // Name of field in a label.
                        .text(name))
                .append($item);
                
            return $li;
        },
        // Function does not modify the model.  Returns an input text object.
        _createInputField: function(name, value, readonly) {
            return $('<input>')
                .addClass('property_values')
                .attr('type', 'text')
                .attr('disabled', readonly)
                .attr('value', value)
                .attr('rhname', name);
        },        
        configureMessage: function (newMessage) {
            // Clear everything in the form and classes
            this.$form.empty().removeClass();
            this.$label.appendTo(this.$form); // Move the label.
            
            var readonly = ('readonly' == newMessage.more.access) ? true : false;
            
            // Represent `value` however is necessary.  Each input text field has an attribute
            // The form's  class will describe the type of data: 
            //    rh_prop_simple
            //    rh_prop_sequence
            //    rh_prop_struct
            //    rh_prop_structsequence
            this.$form.addClass('property');
            if (Object.prototype.toString.call(newMessage.more.value) === '[object Array]') {
                var $olist = $('<ol>').hide();
                if (typeof newMessage.more.value[0] !== 'object') {
                    // Array of the same primitive under the same name.
                    this.$form.addClass('rh_prop_sequence');
                    for (var i in newMessage.more.value) {
                        $olist.append(this._createListItem(
                            "Index " + i, newMessage.more.value[i], i, readonly));
                    }
                }
                else {
                    // Array of structures having the same keys.
                    this.$form.addClass('rh_prop_structsequence');
                    var keys = Object.keys(newMessage.more.value[0]);
                    for (var i in newMessage.more.value) {
                        var $li = $('<li>').append($('<label>').html("Index " + i).addClass('rh_prop_label'));
                        var $ul = $('<ul>').appendTo($li).hide();
                        for (var ki in keys) {
                            $ul.append(this._createListItem(
                                keys[ki], newMessage.more.value[i][keys[ki]], i, readonly));
                        }
                        $olist.append($li);
                    }
                }
                this.$form.append($olist);
            }
            else if (typeof newMessage.more.value === 'object') {
                // message.more.value is a structure with keys.
                this.$form.addClass('rh_prop_struct');
                var $ulist = $('<ul>').hide();
                var keys = Object.keys(newMessage.more.value);
                for (var ki in keys) {
                    $ulist.append(this._createListItem(
                            keys[ki], newMessage.more.value[keys[ki]], 0, readonly));
                }
                this.$form.append($ulist);
            }
            else {
                // Scalar -- add a input text field.
                this.$form.addClass('rh_prop_simple')
                    .append(this._createInputField(
                                newMessage.rhname, 
                                newMessage.more.value, 
                                readonly));
            }
            
            if (!readonly) {
                var $btn = $('<input>')
                    .attr('type', 'button')
                    .attr('value', 'Set')
                    .click($.proxy(this.processFormData, this));
                $btn.insertAfter(this.$label); //this.$form.children('.rh_prop_label'));
            }
            
            this._super(newMessage);
        },
        processFormData: function () {
            var $properties = this.$form.find('.property_values');
            var message = this.options.message;
            message.change = 'update';
            
            if (this.$form.hasClass('rh_prop_simple')) {
                message.more.value = $properties.eq(0).val();
            }
            else if (this.$form.hasClass('rh_prop_struct')) {
                $properties.each(function(index, element) {
                    $element = jQuery(element);
                    // Key -> Set value
                    message.more.value[$element.attr('rhname')] = $element.val();
                });
            }
            else if (this.$form.hasClass('rh_prop_sequence')) {
                $properties.each(function(index, element) {
                    $element = jQuery(element);
                    // Index -> Set value.
                    message.more.value[$element.attr('rhidx')] = $element.val();
                });
            }
            else if (this.$form.hasClass('rh_prop_structsequence')) {
                $properties.each(function(index, element) {
                    $element = jQuery(element);
                    // Index -> Key -> Set value.
                    message.more.value[$element.attr('rhidx')][$element.attr('rhname')] = $element.val();
                });
            }
            else {
                console.error("Property form's class not recognized.");
                return;
            }
            request(message);
        }
    });
})(jQuery);


/* UTILITY FUNCTIONS FOR FEEDBACK AND RH_MESSAGE CHANGES */

/*
 * Client feedback.  This method is for callbacks from client logic.
 * See getActionString() for a convenient way to obtain a string for use
 * in HTML elements (e.g., <input type="button" )
 * @param data An RH_Message conveying a request to the RH Gateway. 
 */
function request(data) {
    console.info("Client sending: " + data.change);
    data = JSON.stringify([data]);
    socket.send(data);
}

/* Creates a request() string which is the one callback defined in
 * the index_template.html file that a client should use to issue
 * messages and commands back to the gateway.
 * 
 * @param msg The reference RH_Message to copy (except for change)
 * @param change The change type to request (update, add, etc.)
 * @param trimMore (optional) If True, more is trimmed to parentID.
 * 
 * @return String capable of being used as DOM Element's event action
 *         (onclick, etc.) pointed at the request() method.
 * 
 */
function getActionString(msg, change, trimMore) {
    var action = msg;
    if (trimMore) {
        action = stripMessage(msg);
    }
    action.change = change;
    return "request(" + JSON.stringify(action) + ")";
}
