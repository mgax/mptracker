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
            var link = $('<a>').attr('href', result['url']).text(name);
            var html = this.item_html(result);
            this.result_list.append(html);
        }, this);
    }

});


})();
