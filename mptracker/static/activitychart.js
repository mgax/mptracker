(function() {
"use strict";


app.render_activitychart = function(options) {
    var box = options.container;
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

    var parseDate = d3.time.format("%Y-%m-%d").parse;

    var x = d3.time.scale()
        .range([0, width]);

    var y = d3.scale.linear()
        .range([height, 0]);

    var color = d3.scale.category10();

    var xAxis = d3.svg.axis()
        .ticks(6)
        .scale(x)
        .orient("bottom");

    var yAxis = d3.svg.axis()
        .ticks(3)
        .tickFormat(d3.format("d"))
        .scale(y)
        .orient("left");

    var line = d3.svg.line()
        .interpolate("linear")
        .x(function(d) { return x(d.date); })
        .y(function(d) { return y(d.value); });

    var vacation_blocks = d3.svg.line()
        .interpolate("step")
        .x(function(d) { return x(d.date); })
        .y(function(d) { return d.vacation ? height : 0 });

    var labels = ['proposals', 'questions'];
    color.domain(labels);

    data.forEach(function(d) {
      d.date = parseDate(d.date);
    });

    var activities = color.domain().map(function(name) {
      return {
        name: name,
        values: data.map(function(d) {
          return {date: d.date, value: +d[name]};
        })
      };
    });

    if(options.one_year) {
      var today = new Date();
      var one_year_ago = new Date();
      one_year_ago.setFullYear(today.getFullYear() - 1);
      x.domain([one_year_ago, today]);
    }
    else {
      x.domain(d3.extent(data, function(d) { return d.date; }));
    }

    y.domain([
        d3.min(activities, function(c) {
            return d3.min(c.values, function(v) { return v.value; }); }),
        d3.max(activities, function(c) {
            return d3.max(c.values, function(v) { return v.value; }); })
    ]);

    svg.append("path")
        .datum(data)
        .attr("class", "activitychart-vacation")
        .attr("d", function(d) { return vacation_blocks(d); })
        .style('fill', '#bbb');

    svg.selectAll(".activity")
        .data(activities)
      .enter().append("path")
        .attr("class", "activitychart-line")
        .attr("d", function(d) { return line(d.values); })
        .style("stroke", function(d) { return color(d.name); });

    svg.append("g")
        .attr("class", "chart-axis x")
        .attr("transform", "translate(0," + height + ")")
        .call(xAxis);

    svg.append("g")
        .attr("class", "chart-axis y")
        .call(yAxis);

    var legend_data = [
        {name: 'întrebări (săptămânal)', color: color('questions')},
        {name: 'propuneri', color: color('proposals')},
        {name: 'vacanță', render: 'block', color: '#bbb'},
    ];

    var legend_item = svg.append('g')
      .selectAll('.activitychart-legend-item')
        .attr('class', 'legend')
        .data(legend_data)
      .enter().append('g')
        .attr('transform', function(d, n) {
            return 'translate(' + (width - 160 - n * 100) + ', -15)'})
        .each(function(d, i) {
            var g = d3.select(this);

            if(d.render == 'block') {
                g.append('rect')
                    .attr('height', 10)
                    .attr('width', 20)
                    .attr('class', 'activitychart-vacation')
                    .style('fill', d.color);
            }
            else {
                g.append('line')
                    .attr('x1', 0)
                    .attr('x2', 20)
                    .attr('y1', 5)
                    .attr('y2', 5)
                    .attr('class', 'activitychart-line')
                    .style('stroke', d.color);
            }

            g.append('text')
                .attr('x', 30)
                .attr('y', 5)
                .attr('dy', '.35em')
                .text(d.name);
        });


    $('.chart-axis.x .tick text').map(function() {
        var el = $(this);
        el.text(app.translate_time(el.text()));
    });
};

})();
