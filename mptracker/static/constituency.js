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
      fillOpacity: 0
    };
  }
});
var senatori_layer = L.geoJson(null, {
  style: function() {
    return {
      weight: '2px',
      opacity: 1,
      fillOpacity: 0
    };
  }
});
map.addLayer(deputati_layer).addLayer(senatori_layer)

$.getJSON(app.constituency.colleges_url, function(data) {
    deputati_layer.addData(
      topojson.feature(data, data.objects['2008-deputati']));
    senatori_layer.addData(
      topojson.feature(data, data.objects['2008-senatori']));
});

var zoom_to_result = function(result) {
  var latlng = result.latlng;
  var content = $('<div>');
  content.append($('<p>').text(result.content));

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

  var popup = new L.Popup();
  map.fitBounds(result.bounds);
  popup.setLatLng(latlng);
  popup.setContent(content.html());
  popup.addTo(map);
  map.openPopup(popup);
};

var geocoding = new L.Geocoding();
map.addControl(geocoding);
$('form[name=geocode]').submit(function(evt) {
  evt.preventDefault();
  var address = $(this).find('[name=address]').val();
  geocoding.options.providers['osm']({
    query: address,
    bounds: map.getBounds(),
    zoom: map.getZoom(),
    cb: zoom_to_result
  });
});

})();
