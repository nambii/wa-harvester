function(doc) {
  for (var i = 0; i < doc.features.length; i++) {
    emit(doc.features[i], 1);
  }
}
