(function() {
"use strict";


app.render_votesimilaritychart = function(options) {
  var margin = {top: 20, right: 20, bottom: 30, left: 60},
      axis_padding = 5,
      width = options.container.width() - margin.left - margin.right,
      height = 300 - margin.top - margin.bottom;

  var data = options.vote_similarity_list;

  var x = d3.scale.ordinal()
      .rangeRoundBands([0, width], .1);

  var y = d3.scale.linear()
      .range([height, 0]);

  var yAxis = d3.svg.axis()
      .scale(y)
      .orient("left")
      .ticks(10, "%");

  var svg = d3.select(options.container[0]).append("svg")
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
    .append("g")
      .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

  x.domain(d3.range(data.length));
  y.domain([0, 1]);

  svg.append("g")
      .attr("class", "y axis")
      .attr("transform", "translate(" + -axis_padding + ",0)")
      .call(yAxis);

  svg.selectAll(".bar")
      .data(data)
    .enter().append("rect")
      .attr("class", "bar")
      .attr("x", function(d, n) { return x(n) - x(0); })
      .attr("width", x.rangeBand())
      .attr("y", function(d) { return y(d.similarity); })
      .attr("height", function(d) { return height - y(d.similarity); })
      .attr("fill", function(d) { return app.PARTY_COLOR[d.party_short_name]; })
      .on("click", clicked)
    .append("svg:title")
      .text(function(d) { return d.name; });

  function clicked(d) {
    window.location.href = '/persoane/' + d.person_slug;
  }
};


})();
