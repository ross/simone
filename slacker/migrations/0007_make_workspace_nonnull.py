'''
Make the workspace FK non-null on Channel and all per-feature models.

This migration must run after 0006_backfill_workspace.py has stamped every
existing row.  If any row still has workspace=NULL (e.g. in a dev environment
where the backfill was skipped), the database-level constraint will be added
anyway; those rows will cause integrity errors on the next write, which is the
correct behaviour (they belong to an unknown workspace and should be cleaned up
or deleted).
'''

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [('slacker', '0006_backfill_workspace')]

    operations = [
        # slacker.Channel
        migrations.AlterField(
            model_name='channel',
            name='workspace',
            field=models.ForeignKey(
                'slacker.Workspace', on_delete=django.db.models.deletion.CASCADE
            ),
        )
    ]
