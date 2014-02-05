(function() {
"use strict";


function random_angle() {
  var steps = 7;
  var max_deviation_angle = 30;
  var angle_step = max_deviation_angle * 2 / (steps - 1);
  return ~~(Math.random() * steps) * angle_step - 2*angle_step;
}


app.render_wordcloud = function(box, word_data) {
  // based on example from https://github.com/jasondavies/d3-cloud
  // and http://www.jasondavies.com/wordcloud/about/

  var width = box.width(), height = box.height() || 10;

  var max = d3.max(word_data, function(pair) { return pair[1]; });
  var min = d3.min(word_data, function(pair) { return pair[1]; });
  var sizeScale = d3.scale.sqrt().domain([min, max]).range([10, 40]);

  d3.layout.cloud().size([width, height])
      .words(
        _.map(shuffle(word_data), function(pair) {
          return {text: pair[0], freq: pair[1]};
        })
      )
      .padding(1)
      .rotate(random_angle)
      .font("Impact")
      .fontSize(function(d) { return sizeScale(d.freq); })
      .on("end", draw)
      .start();

  function draw(words) {
    var svg = d3.select(box[0])
        .append('svg')
        .attr("width", width)
        .attr("height", height)
      .append("g")
        .attr("transform", "translate(" + width/2 + "," + height/2 + ")")
      .selectAll("text")
        .data(words)
      .enter().append("text")
        .style("font-size", function(d) { return sizeScale(d.freq) + "px"; })
        .style("font-family", "Impact")
        .style("fill", "#56b")
        .style("cursor", "pointer")
        .attr("text-anchor", "middle")
        .attr("transform", function(d) {
          return "translate(" + [d.x, d.y] + ")rotate(" + d.rotate + ")";
        })
        .text(function(d) { return d.text; })
        .on("click", function(d) {
          //console.log("click!", d.text);
        });
  }
};


function shuffle(array) {
  // http://bost.ocks.org/mike/shuffle/
  var m = array.length, t, i;
  while(m) {
    i = Math.floor(Math.random() * m--);
    t = array[m];
    array[m] = array[i];
    array[i] = t;
  }
  return array;
}


})();
