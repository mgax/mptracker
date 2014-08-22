(function() {
"use strict";


app.render_groupmember_chart = function(options) {
    var box = $(options.container);
    var data = options.data;
    var margin = 25;
    var width = box.width() - 2*margin;
    var height = 100;

    var svg = d3.select(box[0])
        .append('svg')
        .attr('width', width + 2*margin)
        .attr('height', height + 2*margin)
        .append("g")
          .attr("transform", "translate(" + margin + "," + margin + ")");

    var x = d3.scale.linear()
        .range([0, width])
        .domain(d3.extent(data, function(d) { return d.year; }));

    var y_max = d3.max(data, function(d) { return d.count; });
    var y = d3.scale.linear()
        .range([height, 0])
        .domain([0, Math.ceil(y_max/10) * 10]);

    var xAxis = d3.svg.axis()
        .tickValues(_.pluck(data, 'year'))
        .tickFormat(d3.format("d"))
        .outerTickSize(0)
        .scale(x)
        .orient("bottom");

    var yAxis = d3.svg.axis()
        .tickValues(y.ticks(4).filter(function(t) { return t > 0; }))
        .tickFormat(d3.format("d"))
        .scale(y)
        .orient("left");

    var line = d3.svg.line()
        .interpolate("linear")
        .x(function(d) { return x(d.year); })
        .y(function(d) { return y(d.count); });

    svg.append("path")
        .datum(data)
        .attr("class", "line")
        .attr("d", line);

    svg.append("g")
        .attr("class", "chart-axis x")
        .attr("transform", "translate(0," + height + ")")
        .call(xAxis);

    svg.append("g")
        .attr("class", "chart-axis y")
        .call(yAxis);
};

})();
