function (doc) {
  if (doc.api[0].method == 'GET statuses/user_timeline') {
    emit(doc.user.id_str, doc._id)
  }
}
