// for the outlets database
function(doc) {
  emit(doc.twitter.id_str, doc._id);
}
