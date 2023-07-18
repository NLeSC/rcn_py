

// Define the drag behavior
function zoomstarted(event) {
        // Get current position of network after drag event
        svgTranslate[0] = dx;
        svgTranslate[1] = dy;
    }
function zoomed(event) {
        // Get the real-time scale
        svgScale = event.transform.k;
        zx = svgTranslate[0];
        zy = svgTranslate[1];
        // Update the transform of the network
        svg.attr("transform", `translate(${zx},${zy})  scale(${svgScale})`);
    }
function zoomended(event) {
        // Save the current position after zooming
        curTranslate[0] = zx;
        curTranslate[1] = zy;
    }
  

function canvas_dragstarted(event) {
        isDragging = true;
        // Get the position of canvas at beginning
        svgTranslate[0] = event.x;
        svgTranslate[1] = event.y;
    }
function canvas_dragged(event) {
        if(isDragging) {
            // "event.x - svgTranslate.x" means (current mouse x) - (previous mouse x)
            dx = curTranslate[0] + event.x - svgTranslate[0];
            dy = curTranslate[1] + event.y - svgTranslate[1];

            // Update the transform of the canvas
            svg.attr("transform", `translate(${dx},${dy}) scale(${svgScale})`);
        }
    }
function canvas_dragended(event){
        // Update the starting position for the next drag event
        curTranslate[0] = dx;
        curTranslate[1] = dy;
        isDragging = false;
    }
