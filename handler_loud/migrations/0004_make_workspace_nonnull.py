from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('handler_loud', '0003_add_workspace_fk'),
        ('slacker', '0006_backfill_workspace'),
    ]

    operations = [
        migrations.AlterField(
            model_name='shout',
            name='workspace',
            field=models.ForeignKey(
                'slacker.Workspace', on_delete=django.db.models.deletion.CASCADE
            ),
        )
    ]
