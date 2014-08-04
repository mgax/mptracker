(function() {
"use strict";


app.render_wordcloud = function(box, word_data) {
  // based on example from https://github.com/jasondavies/d3-cloud
  // and http://www.jasondavies.com/wordcloud/about/

  var width = box.width(), height = box.height() || 10;

  var max = d3.max(word_data, function(pair) { return pair[1]; });
  var min = d3.min(word_data, function(pair) { return pair[1]; });
  var sizeScale = d3.scale.sqrt().domain([min, max]).range([10, 40]);

  var tooltip_text = "cuvinte frecvente în declarațiile, inițiativele " +
                     "și întrebările deputatului";

  d3.layout.cloud().size([width, height])
      .words(
        _.map(shuffle(word_data), function(pair) {
          return {text: pair[0], freq: pair[1]};
        })
      )
      .padding(2)
      .rotate(0)
      .font("Impact")
      .fontSize(function(d) { return sizeScale(d.freq); })
      .on("end", draw)
      .start();

  function draw(words) {
    var svg = d3.select(box[0])
        .append('svg')
        .attr("width", width)
        .attr("height", height);

    svg.append('rect')
        .style("fill", "none")
        .style("pointer-events", "all")
        .attr("width", "100%")
        .attr("height", "100%")
      .append('title')
        .text(tooltip_text);

    svg.append("g")
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
        })
        .append('title')
          .text(tooltip_text);
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
