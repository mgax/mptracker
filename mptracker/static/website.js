(function() {
"use strict";


app.template = function(src) {
    return function(vars) {
        return _.template(src, vars, {interpolate: /{{([\s\S]+?)}}/g});
    };
};


app.PersonSearch = Backbone.View.extend({

    item_html: app.template('<li><a href="{{ url }}">{{ name }}</a></li>'),

    events: {
        'submit': 'on_submit'
    },

    initialize: function(options) {
        this.url = options['url'];
    },

    on_submit: function(evt) {
        evt.preventDefault();
        this.query = this.$el.find('[name=query]').val();
        this.update(this.query);
    },

    update: function(query) {
        this.request = $.getJSON(this.url, {q: query});
        this.request.done(_.bind(this.got_update_result, this));
    },

    got_update_result: function(data) {
        this.$el.find('.results').remove();

        if(data['results'].length > 0) {
            var result_list = $('<ul class="list-unstyled results">');
            result_list.appendTo(this.el);
            _(data['results']).forEach(function(result) {
                var link = $('<a>').attr('href', result['url']).text(name);
                var html = this.item_html(result);
                result_list.append(html);
            }, this);
        }
        else {
            var message = $('<p class="results">');
            message.append(
                "Nu am gasit ",
                $('<span>').text(this.query),
                "."
            );
            this.$el.append(message);
        }
    }

});


app.months_en = ["January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"];
app.months_ro = ["ianuarie", "februarie", "martie", "aprilie", "mai", "iunie",
    "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie"];


app.translate_time = function(value) {
    for(var c = 0; c < 12; c ++) {
        value = value.replace(app.months_en[c], app.months_ro[c]);
    }
    return value;
};



app.render_activitychart = function(box, data) {
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

    x.domain(d3.extent(data, function(d) { return d.date; }));

    y.domain([
      d3.min(activities, function(c) { return d3.min(c.values, function(v) { return v.value; }); }),
      d3.max(activities, function(c) { return d3.max(c.values, function(v) { return v.value; }); })
    ]);

    svg.append("path")
        .datum(data)
        .attr("class", "activitychart-vacation")
        .attr("d", function(d) { return vacation_blocks(d); });

    svg.selectAll(".activity")
        .data(activities)
      .enter().append("path")
        .attr("class", "activitychart-line")
        .attr("d", function(d) { return line(d.values); })
        .style("stroke", function(d) { return color(d.name); });

    svg.append("g")
        .attr("class", "activitychart-axis x")
        .attr("transform", "translate(0," + height + ")")
        .call(xAxis);

    svg.append("g")
        .attr("class", "activitychart-axis y")
        .call(yAxis);

    $('.activitychart-axis.x .tick text').map(function() {
        var el = $(this);
        el.text(app.translate_time(el.text()));
    });
};


})();
