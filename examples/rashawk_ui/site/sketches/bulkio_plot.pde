
// This file is part of HAWKEYE.

// HAWKEYE is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.

// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.


// Processing sketch for plotting bulkio streams.
// Inspired by: 
// http://www.instructables.com/id/Drive-a-webpage-in-real-time-using-Arduino-Sensor/step6/Graph-Data-using-Processingjs/

// NxM list of data points processed FIFO.
ArrayList points;

void setup() {
    // Use the system vars and set renderer.
    //size(320, 240, P3D);    // OpenGL-compatible renderer
    size(320, 240);
    
    int rate = 30;
    frameRate(rate);
    MAX_DEPTH = (int) rate * 1.1;
    MIN_DEPTH = (int) rate * 0.9;
    
    points = new ArrayList();
    f = createFont("Arial", 14, true);
    background(backgroundColor);
}

void draw() {
    // Grab the next set of samples and plot with the set options.
    if (0 < points.size()) {
        float[] data = points.get(0);
        drawAGraph(data);
        points.remove(0); 
    }
}

// Append more data to the internal list of data points.
// Target a max buffer depth between MIN_DEPTH and MAX_DEPTH
// to keep the UI responsive to start/stop actions.
int MAX_DEPTH = 40;
int MIN_DEPTH = 20;
int trigger = 0;
int counter = 0;
void addData(float[] data) {
    counter++;
    
    int s = points.size();
    if (MAX_DEPTH <= s) {
        trigger++;
    }
    
    if (MIN_DEPTH >= s) {
        trigger--;
        trigger = max(0, trigger);
    }
    
    if (counter >= trigger) {
        points.add(data);
        counter = 0;
    }
}




// Graph is drawn in offscreen buffers added to the ArrayList
void drawAGraph (float[] data) {
    int len = data.length;
    
    // Slowly converge to the min/max/mid seen in the data set.
    if (autoMinMax) {
        float spread = 1.05;
        yMax = 0.9 * yMax + 0.1 * max(data);
        yMin = 0.9 * yMin + 0.1 * min(data);
        yMax = yMax * spread;
        yMin = yMin * spread;
    }
    
    background(backgroundColor);
    
    // Draw labels
    textFont(f);
    fill(255);
    textAlign(CENTER); 
    rotate(radians(270));
    text(yLabel, -height/2, margin - 5);// Center left, vertical
    rotate(radians(90));
    text(xLabel, width/2, height - 5);// Center bottom.
    
    // Title label
    text(title, width/2, margin);
    
    // DEBUG
    if (debugEnabled) {
        int didx = 2;
        text("yMax:  " + yMax, width/2, margin*didx++);
        text("yMin:  " + yMin, width/2, margin*didx++);
        text("Depth: " + points.size(), width/2, margin*didx++);
    }
    
    // Draw axes lines
    //  |
    //  +----
    stroke(graphLineColor);
    line(margin, 0, margin, height-margin);
    line(margin, height-margin, width, height-margin);
    
    // Draw where 'zero' is in gray
    stroke(180);
    yZero = height - map(0, yMin, yMax, 0, height - margin);
    line(margin, yZero, width, yZero);
    
    // Set line color for the data line.
    stroke(dataLineColor);
    
    int skip = 2;
    int prevX = 0, 
        prevY = 0, 
        thisX = 0, 
        thisY = 0;
    
    // Loop is 1 interval lagged to reduce map() calls.
    // TODO: Add property to use beginShape() -> curveVertex(x,y) -> endShape() for smooth waves.
    for(int p=0, end = len-skip; p<end; p+=skip) {
        thisX = margin + map(p,          0,  len, 0, width - margin);
        thisY = height - map(data[p], yMin, yMax, 0, height - margin);
        
        // Plot.
        if (0 != p) {
            line(prevX, prevY, thisX, thisY);
        }
        
        prevX = thisX;
        prevY = thisY;
    }
}



// Setters for different properties about the graph

// Limits and auto minmax flag to use with map() to scale the data to the view.
float yMax = 2;
float yMin = -yMax;
boolean autoMinMax = true;

// Stroke colors for the lines.
color dataLineColor = color(0, 210, 0);
color graphLineColor = color(255, 255, 255);
color backgroundColor = color(0, 0, 0);

// PFont for labels
PFont f;
String yLabel = "Amplitude";
String xLabel = "Time";
String title =  "BULKIO";
int margin = 25;
boolean debugEnabled = false;


// Set the RGB value for the line color in the plot, 0-255 range.
void setDataLineColor (int r, int g, int b) {
    dataLineColor = color(r, g, b);
}

void setBackgroundColor (int r, int g, int b) {
    backgroundColor = color(r, g, b);
}

void setGraphLineColor (int r, int g, int b) {
    graphLineColor = color(r, g, b);
}

void setYLimits(float newMax, float newMin) {
    yMax = newMax;
    yMin = newMin;
    setAutoYLimits(false);
}

void setAutoYLimits(boolean enabled) {
    autoMinMax = enabled;
}

void setXLabel (String label) {
    xLabel = label;
}

void setYLabel (String label) {
    yLabel = label;
}

void setTitle (String label) {
    title = label;
}

void setEnableDebugPanel(boolean enabled) {
    debugEnabled = enabled;
}
