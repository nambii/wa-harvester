function(doc) {
  if (doc.ogp.wa.publish_time != null) {
    emit(doc.ogp.wa.publish_time, doc.ogp);
  } else {
    emit('0', doc.ogp)
  }
}
