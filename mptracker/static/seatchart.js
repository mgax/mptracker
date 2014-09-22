(function() {
'use strict';

var π = Math.PI;


app.render_seatchart = function(options) {

    var rows = 8,
        rowStep = 3,
        total = options.total,
        highlight = options.highlight,
        minRanks = Math.ceil(total/rows - rowStep*(rows-1)/2),
        margin = 20,
        radius = 200,
        inner = 0.6,
        dotSize = 0.7 * radius * (1 - inner) / (rows - 1),
        width = $(options.container).width(),
        height = margin * 2 + radius * 1.35,
        center = {x: width / 2, y: margin + radius};

    var svg = d3.select(options.container)
      .append('svg')
        .attr('width', width)
        .attr('height', height)
      .append('g')
        .attr('transform', 'translate(' + center.x + ',' + center.y + ')');

    var ranks = function(row) {
        return minRanks + row * rowStep;
    };

    var dots = [];
    d3.range(rows).forEach(function(row) {
        d3.range(ranks(row)).forEach(function(rank) {
            dots.push({
                row: row,
                rank: rank,
            });
        });
    });
    dots = dots.slice(0, total);

    var φScales = d3.range(rows).map(function(row) {
        return d3.scale.linear()
            .range([10/9 * π, - 1/9 * π])
            .domain([0, ranks(row) - 1]);
    });

    var φ = function(d) {
        return φScales[d.row](d.rank);
    };

    dots = _.sortBy(dots, function(d) {
        return - (1000 * φ(d) + d.row);
    });

    dots.forEach(function(d, n) {
        d.n = n;
    });

    highlight.forEach(function(h) {
        dots.slice(h.offset, h.offset + h.count).forEach(function(d) {
            d.color = h.color;
            d.party = h.party;
        });
    });

    var r = d3.scale.linear()
        .range([inner * radius, radius])
        .domain([0, rows - 1]);

    var color = d3.scale.linear()
        .domain([0, dots.length - 1])
        .range(['red', 'blue']);

    svg.selectAll('circle')
        .data(dots)
      .enter().append('circle')
        .style('fill', function(d) { return d.color; })
        .style('cursor', 'pointer')
        .attr('r', dotSize / 2)
        .attr('cx', function(d) { return r(d.row) * Math.cos(φ(d)); })
        .attr('cy', function(d) { return - r(d.row) * Math.sin(φ(d)); })
        .on('click', on_click_dot)
        .append('title')
          .text(function(d) { return d.party; });

    function on_click_dot(d) {
        window.location.href = '/partide/' + d.party;
    }

};


})();
