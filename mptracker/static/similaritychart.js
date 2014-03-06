(function() {
"use strict";

var π = Math.PI;
var sin = Math.sin;
var cos = Math.cos;
function avg(a, b) { return (a + b) / 2; }


function calculateVennDistance(f, debug) {
    var target = π * f / 2;
    var min = 0, max = π / 2;
    var α;
    var operations = "";
    for(var n = 0; n < 50; n ++) {
        α = avg(min, max);
        var estimate = α - sin(α) * cos(α);
        if(estimate > target) {
            max = α;
            operations += "/";
        }
        else {
            min = α;
            operations += "\\";
        }
    }
    var x = 2 * cos(α);
    if(debug) { console.log(operations, f, x, estimate, target); }
    return x;
}


app.render_similaritychart = function(options) {
    var box = options.container;
    var margin = 25;
    var height = 100;
    var width = box.width() - 2*margin;
    var r = 50;

    var svg = d3.select(box[0])
        .append('svg')
        .attr('width', width + 2*margin)
        .attr('height', height + 2*margin)
        .append("g")
          .attr("transform", "translate(" + (margin + 4*r) + "," + margin + ")");

    var x = calculateVennDistance(options.overlap);

    var circle = svg.selectAll("circle")
        .data([{name: 'one', value: 0}, {name: 'two', value: x}]);

    circle.enter().append("circle")
        .attr("r", r)
        .attr("cy", r / 2)
        .attr("cx", function(d) { return r * d.value; })
        .attr("class", function(d) {
            return 'similarity-circle similarity-circle-' + d.name; });
};


})();
