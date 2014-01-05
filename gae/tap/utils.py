import tap

from functools import partial

from django.utils.crypto import salted_hmac

salted_hmac = partial(salted_hmac, secret=tap.config.SECRET_KEY)
