(function() {
"use strict";


app.PersonSearch = Backbone.View.extend({

    events: {
        'submit': 'on_submit'
    },

    initialize: function(options) {
        this.url = options['url'];
        this.result_list = $('<ul class="list-unstyled">').appendTo(this.el);
    },

    on_submit: function(evt) {
        evt.preventDefault();
        var name = this.$el.find('[name=name]').val();
        this.update(name);
    },

    update: function(query) {
        this.request = $.getJSON(this.url, {q: query});
        this.request.done(_.bind(this.got_update_result, this));
    },

    got_update_result: function(data) {
        this.result_list.empty();
        _(data['results']).forEach(function(result) {
            var result_el = $('<li>').text(result['name']);
            this.result_list.append(result_el);
        }, this);
    }

});


})();
