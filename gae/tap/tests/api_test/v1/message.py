from protorpc import messages

class Echo(messages.Message):
  message = messages.StringField(1, required=True)
