(function() {

"use strict";

var attribution = '&copy; <a href="http://osm.org/copyright">'
                + 'OpenStreetMap</a> contributors';
var map = L.map('map').setView([46, 25], 6);

L.tileLayer(
  'http://{s}.tile.osm.org/{z}/{x}/{y}.png',
  {attribution: attribution}
).addTo(map);

var deputati_layer = L.geoJson(null, {
  style: function() {
    return {
      weight: '1px',
      opacity: 1,
      fillOpacity: 0,
      clickable: false
    };
  }
});
var senatori_layer = L.geoJson(null, {
  style: function() {
    return {
      weight: '2px',
      opacity: 1,
      fillOpacity: 0,
      clickable: false
    };
  }
});
map.addLayer(deputati_layer).addLayer(senatori_layer)

map.on('click', function(evt) {
  zoom_to_result({latlng: evt.latlng});
});

$.getJSON(app.constituency.colleges_url, function(data) {
    deputati_layer.addData(
      topojson.feature(data, data.objects['2008-deputati']));
    senatori_layer.addData(
      topojson.feature(data, data.objects['2008-senatori']));
});

var zoom_to_result = function(result) {
  var latlng = result.latlng;
  var content = $('<div>');

  if(result.content) {
    content.append($('<p>').text(result.content));
  }

  var deputati_poly = leafletPip.pointInLayer(latlng, deputati_layer)[0];
  if(deputati_poly) {
    var props = deputati_poly.feature.properties;
    var deputati_key = props['JUD_CODE'] + props['COLDEP'];
    var county_name = app.constituency.county_name[props['JUD_CODE']];

    content.append($('<div>').append($('<b>').text(county_name)));

    var mandate = app.constituency.mandate_data[deputati_key];
    if(mandate) {
      content.append(
        "deputat ",
        "D" + props['COLDEP'] + " ",
        $('<a>', {href: mandate['url']}).text(mandate['name'])
      );
    }
  }

  var senatori_poly = leafletPip.pointInLayer(latlng, senatori_layer)[0];
  if(senatori_poly) {
    var props = senatori_poly.feature.properties;
    content.append($('<div>').append(
      "senator ",
      "S" + props['COLSEN']
    ));
  }

  if(result.bounds) {
    map.fitBounds(result.bounds);
  }
  else {
    map.panTo(result.latlng);
  }
  var html = content.html();
  if(html.length > 0) {
    var popup = new L.Popup();
    popup.setLatLng(latlng);
    popup.setContent(html);
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
    cb: options['success'],
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

})();
