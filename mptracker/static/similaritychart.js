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


app.render_similarity_vote_venn = function(options) {
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

    var percent = Math.round(options.overlap * 100);
    var text = svg
        .append('text')
        .attr('x', -210)
        .attr('y', 30)
        .text("Similaritate la vot: " + percent + "%");

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


var percent_fmt = d3.format("2%"),
    percent_decimal_fmt = d3.format("2.1%");


function percent(value) {
    if(value < .0001 || value > .9999) return percent_fmt(value);
    else if(value < .1 || value > .9) return percent_decimal_fmt(value);
    else return percent_fmt(value);
}


app.render_similarity_barchart = function(options) {

    var margin = {top: 5, right: 100, bottom: 5, left: 160},
        text_margin = 10,
        bar_height = 8,
        bar_margin = 2,
        bar_delta = bar_height + bar_margin,
        width = $(options.container).width(),
        height = margin.top + margin.bottom + bar_margin + 2*bar_height;

    var data = [
        {y: 0, value: options.data.me, class: "me"},
        {y: 1, value: options.data.other, class: "other"}
    ];

    var x = d3.scale.linear()
        .domain([0, 1])
        .range([0, width - margin.left - margin.right]);

    var svg = d3.select(options.container)
      .append("svg")
        .attr("class", "similarity-barchart")
        .attr("width", width)
        .attr("height", height)
      .append("g")
        .attr("transform", "translate(" + margin.left + "," +
                                          margin.top + ")");

    svg.append("text")
        .attr("text-anchor", "end")
        .attr("dx", -text_margin)
        .attr("dy", "1em")
        .text(options.label);

    svg.selectAll(".bar")
        .data(data)
      .enter().append("rect")
        .attr("class", function(d) { return "bar " + d.class; })
        .attr("width", function(d) { return x(d.value); })
        .attr("height", bar_height)
        .attr("transform", function(d, n) {
            return "translate(0," + n * bar_delta + ")"; });

    svg.selectAll(".number")
        .data(data)
      .enter().append("text")
        .attr("class", function(d) { return "number " + d.class; })
        .attr("dx", function(d) { return x(d.value) + text_margin; })
        .attr("dy", function(d, n) { return 7 + n * bar_delta; })
        .text(function(d) { return percent(d.value); });
};


})();
