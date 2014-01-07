window.gettext = (msgid) ->
  return msgid

window.ngettext = (singular, plural, count) ->
  return if count is 1 then singular else plural
