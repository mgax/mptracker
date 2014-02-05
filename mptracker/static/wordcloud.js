(function() {
"use strict";


function random_angle() {
  var steps = 5;
  var max_deviation_angle = 60;
  var angle_step = max_deviation_angle * 2 / (steps - 1);
  return ~~(Math.random() * steps) * angle_step - 2*angle_step;
}


app.render_wordcloud = function(box, word_data) {
  // based on example from https://github.com/jasondavies/d3-cloud
  // and http://www.jasondavies.com/wordcloud/about/
  var fill = d3.scale.category20();

  d3.layout.cloud().size([300, 300])
      .words(
        _.map(word_data, function(pair) {
          return {text: pair[0], size: pair[1]};
        })
      )
      .padding(5)
      .rotate(random_angle)
      .font("Impact")
      .fontSize(function(d) { return d.size; })
      .on("end", draw)
      .start();

  function draw(words) {
    var svg = d3.select(box[0])
        .append('svg')
        .attr("width", 300)
        .attr("height", 300)
      .append("g")
        .attr("transform", "translate(150,150)")
      .selectAll("text")
        .data(words)
      .enter().append("text")
        .style("font-size", function(d) { return d.size + "px"; })
        .style("font-family", "Impact")
        .style("fill", function(d, i) { return fill(i); })
        .attr("text-anchor", "middle")
        .attr("transform", function(d) {
          return "translate(" + [d.x, d.y] + ")rotate(" + d.rotate + ")";
        })
        .text(function(d) { return d.text; });
  }
};


})();
