(function(app) {
"use strict";

app.create_map = function(options) {
  var tileUrl = 'https://cartodb-basemaps-{s}.global.ssl.fastly.net/'
              + 'light_all/{z}/{x}/{y}.png'
  var attribution = '&copy; <a href="https://openstreetmap.org">'
                  + 'OpenStreetMap</a> contributors';
  var map = L.map('map').setView([46, 25], 6);

  L.tileLayer(tileUrl, {attribution: attribution, maxZoom: 18}).addTo(map)

  var judete_layer = L.geoJson(null, {
    style: function() {
      return {
        weight: 1,
        opacity: .4,
        fillOpacity: 0,
        clickable: false
      };
    }
  });
  map.addLayer(judete_layer);

  map.on('click', function(evt) {
    zoom_to_result({latlng: evt.latlng});
  });

  $.getJSON(options.judete_url, function(data) {
      judete_layer.addData(
        topojson.feature(data, data.objects['judete']));
  });

  var zoom_to_result = function(result) {
    var latlng = result.latlng;
    var content = $('<div>');

    if(result.content) {
      content.append($('<p>').text(result.content));
    }

    var judete_poly = leafletPip.pointInLayer(latlng, judete_layer)[0];
    if(judete_poly) {
      var props = judete_poly.feature.properties;
      var jud_code = options.county_code_map[props['id']]
      var judete_key = jud_code;
      var county_name = options.county_name[jud_code];

      content.append($('<div>').append($('<b>').text(county_name)));

      var mandate_list = options.mandate_data[judete_key];
      if(mandate_list) {
        content.append("deputat ");
        for(var c = 0; c < mandate_list.length; c ++) {
          var mandate = mandate_list[c];
          content.append(
            $('<a>', {href: mandate['url']}).text(mandate['name'])
          );
          if(c + 1 < mandate_list.length) {
            content.append(', ');
          }
        }
      }
    }

    if(judete_poly) {
      if(result.bounds) {
        map.fitBounds(result.bounds);
      }
      else {
        map.panTo(result.latlng);
      }
      var popup = new L.Popup();
      popup.setLatLng(latlng);
      popup.setContent(content.html());
      popup.addTo(map);
      map.openPopup(popup);
    }
  };

  var orig_button_text = $('form[name=geocode] button').text();

  var geocoding = new L.Geocoding();
  map.addControl(geocoding);

  function geocode(options) {
    geocoding.options.providers[options['provider']]({
      query: options['address'],
      bounds: map.getBounds(),
      zoom: map.getZoom(),
      cb: function(result) {
        if(judete_layer.getBounds().contains(result.latlng)) {
          options['success'](result);
        }
        else {
          options['error']();
        }
      },
      cb_err: options['error']
    });
  }

  $('form[name=geocode]').submit(function(evt) {
    evt.preventDefault();
    var form = $(this);
    var input = form.find('[name=address]');
    var button = form.find('button');

    var address = input.val();

    button.text('...').attr('disabled', true);
    form.removeClass('has-error has-success');

    var geocode_end = function() {
      button.text(orig_button_text).attr('disabled', false);
    };

    var geocode_success = function(result) {
      geocode_end();
      form.removeClass('has-error').addClass('has-success');
      zoom_to_result(result);
    };

    var geocode_failure = function() {
      geocode_end();
      form.addClass('has-error');
    };

    geocode({
      address: address,
      provider: 'osm',
      success: geocode_success,
      error: function() {
        geocode({
          address: address,
          provider: 'google',
          success: geocode_success,
          error: geocode_failure
        });
      }
    });
  });
};

})(window.app);
