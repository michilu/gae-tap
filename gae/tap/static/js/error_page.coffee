$ () ->
  count = 1
  limit = 29000
  interval = 300
  $seconds = $("#seconds")
  setInterval(() ->
    value = count / (limit / interval) * 100
    $seconds.css("width", "#{value}%")
    count += 1
  , interval)

  return
