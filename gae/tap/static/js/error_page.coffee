$ () ->
  count = 1
  limit = 29000
  interval = 300
  $seconds = $("#seconds")

  indicator = () ->
    value = count / (limit / interval) * 100
    if value > 100
      return
    $seconds.css("width", "#{value}%")
    count += 1
    setTimeout indicator, interval
    return
  indicator()

  return
