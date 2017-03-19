function(doc) {
  for(var i = 0; i < doc.entities.urls.length; i++) {
    emit(doc.entities.urls[i].expanded_url, 1);
  }
}
