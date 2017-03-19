function (doc) {
  if (doc.wa != null) {
    if (doc.wa.outlet != null) {
      emit(doc._id, doc.wa.outlet)
    }
  }
}
