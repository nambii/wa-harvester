function(keys, values, rereduce) {
  var have_doc = false;
  for (i=0;i<values.length;i++) {
    if (values[i] == 0) {
      have_doc = true;
    }
  }
  if (have_doc) {
    return 0;
  } else {
    return 1;
  }
}
