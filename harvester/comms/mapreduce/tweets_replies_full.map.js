function(doc) {
  if (doc.in_reply_to_user_id_str != null) {
    if (doc.in_reply_to_status_id_str != null) {
      emit([doc.in_reply_to_status_id_str, doc.id_str, doc.user.id_str], 1);
    }
  }
  emit([doc._id, doc.id_str, doc.user.id_str], 0);
}
