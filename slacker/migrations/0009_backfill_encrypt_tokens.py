'''
Data migration: re-save every Workspace to encrypt any plaintext bot_token
values that were written before 0008_encrypt_bot_token introduced at-rest
encryption.

The EncryptedField has a decrypt-with-fallback: if from_db_value cannot
decrypt the stored bytes it returns them as-is (treating them as legacy
plaintext).  Calling save() here triggers get_prep_value, which encrypts the
(already decrypted or legacy-plaintext) value and writes it back.

Reverse: no-op — we do not attempt to decrypt and re-store as plaintext on
rollback.  Rows remain encrypted if this migration is rolled back, which is
safe (the fallback path reads them correctly with the key still in settings).
'''

from django.db import migrations


def encrypt_tokens(apps, schema_editor):
    Workspace = apps.get_model('slacker', 'Workspace')
    count = 0
    for ws in Workspace.objects.all():
        ws.save(update_fields=['bot_token'])
        count += 1
    if count:
        print(
            f'\n  [encrypt_tokens] Encrypted bot_token for {count} workspace(s)'
        )


def no_op(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [('slacker', '0008_encrypt_bot_token')]

    operations = [migrations.RunPython(encrypt_tokens, no_op)]
