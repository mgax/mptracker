(function() {
"use strict";

app.stats_slider = function(options) {
    var $frame = options.$el;
    var interval = 1000 * options.interval |0;
    var $page_list = $frame.find('.stats-slider-page').remove();
    var $current_page = null;
    var page = (((new Date()).valueOf() / interval) |0) % 3;

    function next() {
        if($current_page) {
            $current_page.css('z-index', 1);
            $current_page.animate({left: -400, right: 400}, 500, function() {
                $(this).remove();
            });
        }
        page = (page + 1) % $page_list.length;
        $current_page = $page_list.eq(page).clone();
        $frame.append($current_page.show());
    }

    next();
    setInterval(next, interval);

    return {
        next: next
    }
};


})();
