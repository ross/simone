'''
Schema migration: change bot_token from CharField(max_length=255) to
EncryptedField (backed by a TEXT column).

The column type change to TEXT is needed because Fernet ciphertext is
significantly longer than the plaintext it encodes.  The follow-up migration
(0009) re-saves every existing Workspace to encrypt the plaintext tokens that
were stored before this migration.
'''

from django.db import migrations
import slacker.fields


class Migration(migrations.Migration):

    dependencies = [('slacker', '0007_make_workspace_nonnull')]

    operations = [
        migrations.AlterField(
            model_name='workspace',
            name='bot_token',
            field=slacker.fields.EncryptedField(),
        )
    ]
