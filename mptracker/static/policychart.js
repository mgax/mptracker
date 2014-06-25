(function() {
'use strict';


app.render_policy_chart = function(options) {

    var width = $(options.container).width(),
        margin = 20,
        height = 300,
        radius = d3.min([width, height]) / 2 - margin;

    var percent = d3.format("2%");

    var arc = d3.svg.arc()
        .outerRadius(radius)
        .innerRadius(radius / 2);

    var pie = d3.layout.pie()
        .sort(null)
        .value(function(d) { return d.interest; });

    var svg = d3.select(options.container)
      .append('svg')
        .attr('class', 'policy-chart')
        .attr('width', width)
        .attr('height', height);

    var pie_g = svg.append('g')
        .attr('transform', 'translate(' + width / 2 + ',' + height / 2 + ')');

    var arc_g = pie_g.selectAll('arc')
        .data(pie(options.data))
      .enter().append('g')
        .attr('class', 'arc');

    arc_g.append('path')
        .attr('d', arc)
        .attr('class', function(d) { return 'policy-' + d.data.slug; })
      .append('title')
        .text(function(d) { return d.data.name; });

    arc_g.append('text')
        .attr('transform', function(d) {
            return 'translate(' + arc.centroid(d) + ')'; })
        .text(function(d) { return percent(d.data.interest); })
      .append('title')
        .text(function(d) { return d.data.name; });
};


})();
