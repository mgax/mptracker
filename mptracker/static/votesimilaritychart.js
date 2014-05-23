(function() {
"use strict";


app.render_votesimilaritychart = function(options) {
    options.container.text(JSON.stringify(options.vote_similarity_list));
};


})();
