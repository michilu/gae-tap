(() ->
  translation = "{{ translation|safe }}"

  window.gettext = (msgid) ->
    value = get_value_from_translation translation, msgid
    if value?
      return if typeof(value) is "string" then value else value[0]
    else
      return msgid

  window.ngettext = (singular, plural, count) ->
    value = get_value_from_translation translation, singular
    if value?
      return value[plural_index(count, translation)]
    else
      return if count is 1 then singular else plural

  get_value_from_translation = (translation, msgid) ->
    ret = translation.catalog?[msgid]
    if not ret? and translation.fallback?
      ret = get_value_from_translation translation.fallback, msgid
    return ret

  plural_index = (count, translation) ->
    eval "var n = #{count}; var v = #{translation.plural}"
    return v

  return
)()
