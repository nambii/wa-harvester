function (key, values, rereduce) {
  var max = -Infinity
  for (var i = 0; i < values.length; i++)
    if (values[i] > max)
      max = values[i]
  return max
}
