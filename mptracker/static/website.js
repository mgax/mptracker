(function() {
"use strict";


app.template = function(src) {
    var options = {
        interpolate: /{{([\s\S]+?)}}/g,
        evaluate: /{%([\s\S]+?)%}/,
    };
    return function(vars) {
        return _.template(src, vars, options);
    };
};


app.PersonSearch = Backbone.View.extend({

    item_html: app.template(
        '<li>' + '<a href="{{ url }}">{{ name }}</a> ' +
        '{% if(count) { %}({{ count }}){% } %}' +
        '</li>'
    ),

    events: {
        'submit': 'on_submit'
    },

    initialize: function(options) {
        this.url = options['url'];
    },

    on_submit: function(evt) {
        evt.preventDefault();
        var pairs = _.values(this.$el.serializeArray());
        var query = _.object(_.pluck(pairs, 'name'), _.pluck(pairs, 'value'));
        this.update(query);
    },

    update: function(query) {
        this.request = $.getJSON(this.url, query);
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
            message.text("Nu am găsit nicio persoană.");
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

})();
