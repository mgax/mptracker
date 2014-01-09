(function() {
"use strict";


var color = {
    "Indep.": "#eee",
    "Mino.": "#888",
    "PC": "#3e99ff",
    "PDL": "#ff962d",
    "PNL": "#e9e900",
    "PP-DD": "#5a167b",
    "PSD": "#f00",
    "UDMR": "#005900"
};


app.render_membershipchart = function(box, data) {
    var margin = 25;
    var width = box.width() - 2*margin;
    var height = 20;

    var svg = d3.select(box[0])
        .append('svg')
        .attr('width', width + 2*margin)
        .attr('height', height + 2*margin)
        .append("g")
          .attr("transform", "translate(" + margin + "," + margin + ")");

    var parseDate = d3.time.format("%Y-%m-%d").parse;

    var x = d3.time.scale()
        .range([0, width]);

    var xAxis = d3.svg.axis()
        .ticks(6)
        .scale(x)
        .orient("bottom");

    var vacation_blocks = d3.svg.line()
        .interpolate("step")
        .x(function(d) { return x(d.date); })
        .y(function(d) { return d.vacation ? height : 0 });

    var labels = ['proposals', 'questions'];

    var last_day = new Date();
    last_day.setDate(last_day.getDate() + 7);
    last_day = d3.time.monday(last_day);

    data.forEach(function(d) {
      d.start_date = parseDate(d.start_date);
      d.end_date = _.min([parseDate(d.end_date), last_day]);
    });

    x.domain([parseDate('2012-12-17'), parseDate('2016-12-5')]);

    var tooltip = d3.tip().html(function(d) { return d.group_short_name; });
    svg.call(tooltip);

    svg.selectAll(".activity")
        .data(data)
      .enter().append("rect")
        .attr("class", "membershipchart-rect")
        .attr('x', function(d) { return x(d.start_date); })
        .attr('width', function(d) { return x(d.end_date) - x(d.start_date); })
        .attr('y', 0)
        .attr('height', height)
        .on('mouseover', tooltip.show)
        .on('mouseout', tooltip.hide)
        .on('click', function(d) { navigate_to_group(d); })
        .style("fill", function(d) { return color[d.group_short_name]; });

    svg.append("g")
        .attr("class", "chart-axis x")
        .attr("transform", "translate(0," + height + ")")
        .call(xAxis);

    $('.chart-axis.x .tick text').map(function() {
        var el = $(this);
        el.text(app.translate_time(el.text()));
    });

    function navigate_to_group(d) {
        if(d.group_short_name != 'Indep.') {
            window.location.href = '/partide/' + d.group_id;
        }
    }
};

})();
