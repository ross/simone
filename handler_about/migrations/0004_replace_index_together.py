from django.db import migrations, models

# Django 5.1 removed the `index_together` Meta option, so the model now
# declares this same composite index via `Meta.indexes` instead. The name
# below is the one Django's schema editor deterministically assigned to the
# old index_together-based index (a hash of the table + column names, so
# it's the same on every backend) when it was created back in
# 0002_add_workspace_fk. On SQLite it no longer actually exists — the
# 0003_make_workspace_nonnull AlterField rebuilt the table, and SQLite's
# table-rebuild only restores indexes tracked via Meta.indexes, silently
# dropping the index_together one — but on MySQL it's still present, so we
# look for it by name and drop it if we find it.
LEGACY_INDEX_NAME = (
    'handler_about_fact_workspace_id_user_id_created_at_cff0afa0_idx'
)
NEW_INDEX_NAME = 'handler_abo_workspa_4d097e_idx'


def drop_legacy_index(apps, schema_editor):
    Fact = apps.get_model('handler_about', 'Fact')
    table = Fact._meta.db_table
    with schema_editor.connection.cursor() as cursor:
        constraints = schema_editor.connection.introspection.get_constraints(
            cursor, table
        )
    if LEGACY_INDEX_NAME in constraints:
        schema_editor.remove_index(
            Fact,
            models.Index(
                fields=['workspace', 'user_id', 'created_at'],
                name=LEGACY_INDEX_NAME,
            ),
        )


class Migration(migrations.Migration):

    dependencies = [('handler_about', '0003_make_workspace_nonnull')]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterIndexTogether(
                    name='fact', index_together=set()
                ),
                migrations.AddIndex(
                    model_name='fact',
                    index=models.Index(
                        fields=['workspace', 'user_id', 'created_at'],
                        name=NEW_INDEX_NAME,
                    ),
                ),
            ],
            database_operations=[
                migrations.RunPython(
                    drop_legacy_index, migrations.RunPython.noop
                ),
                migrations.AddIndex(
                    model_name='fact',
                    index=models.Index(
                        fields=['workspace', 'user_id', 'created_at'],
                        name=NEW_INDEX_NAME,
                    ),
                ),
            ],
        )
    ]
