from logging import getLogger

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models

log = getLogger('EncryptedField')


def _fernet():
    key = getattr(settings, 'SIMONE_TOKEN_KEY', None)
    if not key:
        raise RuntimeError(
            'SIMONE_TOKEN_KEY must be configured to use EncryptedField'
        )
    return Fernet(key)


class EncryptedField(models.TextField):
    '''
    A TextField that transparently encrypts/decrypts values using Fernet
    symmetric encryption (AES-128-CBC + HMAC-SHA256).

    The encryption key is read from settings.SIMONE_TOKEN_KEY (a Fernet key,
    i.e. a URL-safe base64-encoded 32-byte value).

    Decrypt-with-fallback: if a stored value cannot be decrypted (e.g. it was
    written before encryption was enabled), it is returned as-is.  This allows
    a zero-downtime migration where existing plaintext rows are still readable
    while new writes are encrypted.  The backfill migration re-saves every row
    to encrypt the legacy plaintext values.
    '''

    def get_prep_value(self, value):
        if value is None:
            return value
        f = _fernet()
        return f.encrypt(value.encode()).decode()

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        f = _fernet()
        try:
            return f.decrypt(value.encode()).decode()
        except (InvalidToken, Exception):
            # Legacy plaintext value (pre-encryption) — return as-is so the
            # backfill migration can read and re-save it.
            log.debug('from_db_value: decrypt failed, returning raw value')
            return value
