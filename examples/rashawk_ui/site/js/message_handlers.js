/**
 * @author Thomas Goodwin and Joe Reinhart
 * 
 * @description
 *   The RasHawk APG Challenge will override the domain handler to 
 *   build the main menu and Google Maps interfaces (if necessary).
 *   The Device and some of its children will be represented as icons
 *   on the map until "onhover" at which point more details will show.
 */

/* 
 * @description
 *   
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

   
/* 
 * JQUERY and Google Wrapper interface
 */
jQuery.noConflict();
(function($) {
    // Rashawk-inspired Google Maps API V3 wrapper from Joe Reinhart
    var RasHawk_Map_Wrapper = function(using_id, center_lat, center_lon) {
        this.map_id = using_id;
        this.focusOnFirstStreamChange = true;
        this.markers = {};
        this.center_pos = new google.maps.LatLng(center_lat, center_lon);
        this.bounds = new google.maps.LatLngBounds(this.center_pos, this.center_pos); 
       
        var mapOptions = { 
            center: this.center_pos,
            zoom: 16, 
            mapTypeId: google.maps.MapTypeId.HYBRID
        };  
        
        
        var thediv = document.getElementById(this.map_id);
        this.map = new google.maps.Map(thediv,  mapOptions);
        
        // TODO: Solve mystery of why focusView must a be used as below rather than:
        // .click(this.focusView)
        // .click($.proxy(this.focusView, this))
        // .on('click', this.focusView)
        // ... etc.  All the other typical mechanisms that seem to work.
        var inst = this;
        this.$counter = $('<div>').pi_counter()
            .attr('id', 'rashawk_pi_counter')
            .addClass('rashawk_above_map')
            .insertBefore(thediv);
        this.$focus_btn = $('<input>')
            .attr('id', 'rashawk_focus_view')
            .addClass('rashawk_above_map')
            .attr('type', 'button')
            .attr('value', 'Focus View')
            .click($.proxy(function() { this.focusView(); }, this)) // Erm...?
            .insertBefore(thediv);
        
        // Methods
        
        // Process a message (callback for widget events and direct method)
        this.updateView = function(message) {             
            if ('device_manager' == message.rhtype) {
                // Add/remove markers 
                if ('add' == message.change) {
                    var markerX = new google.maps.Marker({
                        position: new google.maps.LatLng(0, 0),
                        map: this.map,
                        title: message.rhname,
                        icon: "images/pi.png",
                    });
                    // Stored by node instance name: raspberry_piXX
                    this.markers[message.rhname] = markerX;
                    this.$counter.pi_counter('incrementCounter');
                }
                else if ('remove' == message.change) {
                    if ((message.rhname in this.markers) && 
                        this.markers.hasOwnProperty(message.rhname)) {
                        // // // 
                        // Delete the marker.
                        this.markers[message.rhname].setMap(null);
                        delete this.markers[message.rhname];
                        this.$counter.pi_counter('decrementCounter');
                    }
                }
            }
            else if (('port' == message.rhtype) &&
                     ('stream' == message.change)) {
                // Port's parentID is raspberry_piXX:GPS_ID
                var pname = message.more.parentID.replace(/:GPS_ID/,'');
                if ((pname in this.markers) && this.markers.hasOwnProperty(pname)) {
                    // Update marker position using parentID.  First "stream" is just an ack
                    // so we check for valid values parsed from the data.
                    if ((('latitude' in message.more.data)  && message.more.data.hasOwnProperty('latitude')) && 
                        (('longitude' in message.more.data) && message.more.data.hasOwnProperty('longitude'))) {
                        // // // //
                        // Message data should be okay, attempt to parse it.
                        var lat = parseFloat(message.more.data.latitude);
                        var lon = parseFloat(message.more.data.longitude);
                        if ((NaN != lat) && (NaN != lon)) {
                            this.markers[pname].setPosition(
                                new google.maps.LatLng(lat, lon));
                            
                            if ((1 == this.$counter.pi_counter('currentCount')) && 
                                (this.focusOnFirstStreamChange)) {
                                // // // // 
                                // On the first received stream, set the center position to the first
                                // node's position that was announced to help center the UI automatically.
                                this.focusOnFirstStreamChange = false;
                                this.center_pos = new google.maps.LatLng(lat, lon);
                                this.focusView();
                            }
                        }
                    }
                }
            }
        };
        this.updateView_cb = function(event, message) { 
            this.updateView(message); 
        };
        
        // Center on markers.
        this.focusView = function() {
            var latmin = this.center_pos.lat(),
                latmax = this.center_pos.lat(),
                lonmin = this.center_pos.lng(),
                lonmax = this.center_pos.lng();
            diff = 0.0;
            
            for (key in this.markers) {
                if (this.markers[key].position.lat() < latmin) {
                    diff = latmin - this.markers[key].position.lat();
                    latmin -= diff;
                    latmax += diff;
                }
                if (this.markers[key].position.lat() > latmax) {
                    diff = this.markers[key].position.lat() - latmax;
                    latmin -= diff;
                    latmax += diff;
                }
                if (this.markers[key].position.lng() < lonmin) {
                    diff = lonmin - this.markers[key].position.lng();
                    lonmin -= diff;
                    lonmax += diff;
                }
                if (this.markers[key].position.lng() > lonmax) {
                    diff = this.markers[key].position.lng() - lonmax;
                    lonmin -= diff;
                    lonmax += diff;
                }
            }
            this.bounds.extend(new google.maps.LatLng(latmin, lonmin), 
                               new google.maps.LatLng(latmax, lonmax));
            this.map.fitBounds(this.bounds);
            
            // Update "server_pos" to be the new estimated center around the Pis.
            this.center_pos = this.map.getCenter();
        };
    };
    
    
    // Wrapper for Processing.js plot object.
    // @param parent_id the ID of the DIV that can contain this canvas.
    // @param driver_id is the ID of the object driving the stream
    //                  The cleanRHID version will be the canvas's ID in the DOM.
    var RasHawk_Plot_Wrapper = function (parent_id, driver_id) {
        this.driver_id = driver_id;
        this.clean_id = function() { return cleanRHID(this.driver_id); };
        
        var $parent = $('#' + parent_id);
        this.$container = $('<div>').addClass('rashawk_plot');
        var $canvas = $('<canvas>').attr('id', this.clean_id());
        this.$container.append($canvas);
        $parent.append(this.$container);
        
        // Attach to processing.js once the canvas can be found in the div.
        this.plotter = null;
        this.closing = false;
        Processing.loadSketchFromSources(this.clean_id(), ["/sketches/bulkio_plot.pde"]);
        this.bind = function() {
            this.plotter = Processing.getInstanceById(this.clean_id());
            if ((null == this.plotter) && !this.closing) {
                setTimeout($.proxy(this.bind, this), 500);
            }
            else {
                // Set other options... labels, limits, etc.
                this.plotter.setYLimits(128, -127);
                this.plotter.setTitle(this.driver_id.substring(0, this.driver_id.indexOf(':')));
                this.plotter.setBackgroundColor(  20, 20,  20); // Charcoal
                this.plotter.setDataLineColor(   182, 18,  26); // Redhawk Red
                this.plotter.setGraphLineColor(    0, 85, 129); // Geon blue
            }
        };
        this.bind();
        
        this.cleanup = function() { 
            this.closing = true;
            this.$container.remove();
            if (null != this.plotter)
                this.plotter.exit();
        };
        
        // Callback for processing incoming messages.
        // The Processing.js plotter will filter the stream to maintain frame rate.
        this.processMessage = function (message) {
            if (null != this.plotter) {
                if ('stream' == message.change) {
                    var size = message.more.data.length;
                    if (0 < size) {
                        for (var i = 0; i < size; i++) {
                            this.plotter.addData(message.more.data[i]);
                        }
                    }
                }
            }
        };
    };
    
    // Frontend for managing multiple concurrent plots.
    var RasHawk_Plots_Mgr = function (parent_id) {
        this.parent_id = parent_id;
        this.plotters = [];
        
        this._findPlotter = function (id) {
            var len = this.plotters.length;
            var idx = -1;
            for (i = 0; i < len; i++) {
                if (this.plotters[i].driver_id == id) {
                    idx = i;
                    break;
                }
            }   
            return idx;
        };
        
        // Process stream messages from ports.  
        // Uses ev.target.id to maintain this.plotters
        this.processMessage_cb = function (ev, message) {
            if ('stream' == message.change) {
                var idx = this._findPlotter(ev.target.id);
                
                if (0 == message.more.data.length) {
                    // Add
                    if (0 > idx) {
                        this.plotters.push(new RasHawk_Plot_Wrapper(this.parent_id, ev.target.id));
                    }
                }
                else {
                    // Update.
                    if (-1 < idx) {
                        this.plotters[idx].processMessage(message);
                    }
                }
            }
            else if ('update' == message.change) {
                // Remove.
                var idx = this._findPlotter(ev.target.id);
                if (-1 < idx) {
                    this.plotters[idx].cleanup();
                    this.plotters.splice(idx, 1);
                }
            }
        };
    };
    
    // Setup the maps api wrapper
    var TheWrapperInstance = null;
    var ThePlotters = new RasHawk_Plots_Mgr("rashawk_plots");
    $(document).ready(function() {
        if (null == TheWrapperInstance) {
            TheWrapperInstance = new RasHawk_Map_Wrapper(
                'map-canvas', 39.17926730, -76.6684619); // BWI
            
            // Setup the device manager menu using one of the provided REDHAWK jQuery widgets.
            $('#rashawk_nodes').default_container({labelText: 'RasHawk Management'});
            
            // Use the Redhawk defualt container widget for a show/hide of plots when present.
            $('#rashawk_plots').default_container({labelText: 'RasHawk Plots'});
        }
    });
   
    // Some custom widgets for the mapping interface, node_info, etc.
    $.widget("rashawk.pi_counter", {
        _create: function() {
            this.$heading = $('<span>').html("RasHawks: ");
            this.$count = $('<span>').html('0');
            this.$heading.append(this.$count);
            this.element.append(this.$heading);
        },
        incrementCounter: function () {
            var count = parseInt(this.$count.html()) + 1;
            this.$count.html(count);            
        },
        decrementCounter: function () {
            var count = parseInt(this.$count.html()) - 1;
            this.$count.html(count);
        },
        currentCount: function () {
            return parseInt(this.$count.html());
        }
    });
    
    /* Returns `true` if the parent's container was rendered, `false` otherwise */
    function parentIsRendered (parentRHID) {
        return (0 < $('#' + cleanRHID(parentRHID)).length);
    }
    
    /*
     * Implementing a few message handlers.
     */
    messageHandlers = {
        // Dropping messages for these types
        domain : function (message) { return null; },
        service: function (message) { return null; },
        
        // TODO: Implement these handlers as a separate menu.
        application: function (message) { return null; },
        component:   function (message) { return null; },
        
        // Render default if parent exists        
        device : function (message) {
            var $container = null;
            if (parentIsRendered(message.more.parentID)) {
                switch (message.rhname) {
                    case "gps_receiver":
                    case "rtl_sdr_device":
                        // Create the typical container, remove the _group divs.
                        $container = $('<div>')
                            .device_container({message: message});
                        $container.children("[class$='_group']").remove();
                        $container.hide();
                    default:
                        break;
                }
            }
            else {
                console.warn("Dropped message: "); console.warn(message);
            }
            return $container;
        },
        property : function (message) {
            var $container = null;
            if (parentIsRendered(message.more.parentID)) {
                // parentID for properties will contain a concatenation leading up to the device.
                // in question.  Only render these properties from the RTL.
                if (-1 !== message.more.parentID.indexOf('RTL_ID')) {
                    switch (message.rhname) {
                        case 'center_frequency' :
                        case 'sample_rate' :
                            $container = $('<div>').property_container({message: message}).hide();
                        default:
                            break;
                    }
                }
            }
            else {
                console.warn("Dropped message: "); console.warn(message);
            }
            return $container;
        },
        
        // (extra) Special implementations tying events to other aspects of the UI.
        
        // Drop all device managers other than those starting with raspberry_pi
        // Attach message_configured to TheWrapperInstance's callback.
        device_manager  : function (message) {
            var $container = null;
            if (message.rhname.lastIndexOf('raspberry_pi', 0) === 0) {
                $container = $('<div>')
                    .device_manager_container(
                        {message: message,
                         configured: $.proxy(TheWrapperInstance.updateView_cb, 
                                             TheWrapperInstance)});
                                             
                // Add a "refresh"  button to request an update, if necessary.
                var $refresh = $('<input type="button">')
                    .addClass('refresh')
                    .attr('value', 'Refresh')
                    .attr('onclick', getActionString(message, 'update', true))
                    .insertAfter($container.children('.show_hide'));
            }
            else {
                console.warn("Dropped message: "); console.warn(message);
            }
            return $container;
        },
        
        // Hook GPS ports to TheWrapperInstance via the message_configured event.
        port : function(message) {
            var $container = null;
            if (parentIsRendered(message.more.parentID)) {
                // parentID is a concatenation of UUIDs leading up to the Device.
                if (-1 !== message.more.parentID.indexOf('GPS_ID')) {
                    if ('GPS_idl' == message.rhname) {
                        // Grab only the GPS port.
                        // Generate a 'start' stream request, create the element, and hide it.
                        // This allows it to still receive updates which are then forwarded
                        // to the Google Canvas widget.
                        var streamRequest = stripMessage(message);
                        streamRequest.change = 'start';
                        request(streamRequest);
                        $container = $('<div>')
                            .port_container(
                                {message: message,
                                 configured: $.proxy(TheWrapperInstance.updateView_cb, 
                                                             TheWrapperInstance)})
                            .hide();
                    }
                }
                else if (-1 !== message.more.parentID.indexOf('RTL_ID')) {
                    // Grab only the dataShort_Out port
                    if ('dataShort_Out' == message.rhname) {
                        $container = $('<div>').port_container(
                                {message: message, 
                                 configured: $.proxy(ThePlotters.processMessage_cb, ThePlotters)})
                            .hide();
                    }
                }
            }
            else {
                console.warn("Dropped message: "); console.warn(message);
            }
            // Return whatever it is...null or otherwise.
            return $container;
        }
    };
    
    parentIDOverrides = {
        device_manager: 'rashawk_nodes'
    };
})(jQuery);
