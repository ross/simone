'''
Data migration: backfill existing single-workspace data.

When SLACK_BOT_TOKEN is present in the environment, call auth.test to
discover the team_id for the current workspace, create a Workspace row,
and stamp every existing Channel, Fact, Item, Shout, Trigger, and
sparkles.User with that workspace.

If SLACK_BOT_TOKEN is absent (test/dev environments without real creds)
the migration is a no-op — existing rows keep workspace=NULL, which is
harmless in an otherwise-empty dev database.
'''

from os import environ

from django.db import migrations


def backfill(apps, schema_editor):
    token = environ.get('SLACK_BOT_TOKEN', '')
    if not token:
        print(
            '\n  [backfill_workspace] SLACK_BOT_TOKEN not set; skipping backfill. '
            'Run with SLACK_BOT_TOKEN=<your-token> to backfill existing data.'
        )
        return

    from slack_sdk import WebClient

    client = WebClient(token=token)
    resp = client.auth_test()
    if not resp['ok']:
        raise RuntimeError(
            f'auth.test failed: {resp.get("error", "unknown error")}'
        )

    team_id = resp['team_id']
    team_name = resp.get('team', '')
    bot_user_id = resp.get('user_id', '')
    bot_id = resp.get('bot_id', '')

    Workspace = apps.get_model('slacker', 'Workspace')
    from django.utils import timezone

    workspace, created = Workspace.objects.get_or_create(
        team_id=team_id,
        defaults={
            'team_name': team_name,
            'bot_token': token,
            'bot_id': bot_id,
            'bot_user_id': bot_user_id,
            'bot_scopes': '',
            'installed_at': timezone.now(),
        },
    )
    if created:
        print(
            f'\n  [backfill_workspace] Created Workspace team_id={team_id} ({team_name})'
        )
    else:
        # Already exists (e.g. if the OAuth flow already ran); update bot_token.
        workspace.bot_token = token
        workspace.bot_user_id = bot_user_id
        workspace.bot_id = bot_id
        workspace.save()
        print(
            f'\n  [backfill_workspace] Updated existing Workspace team_id={team_id}'
        )

    # Stamp every existing row with the resolved workspace.
    for model_label in [
        ('slacker', 'Channel'),
        ('handler_about', 'Fact'),
        ('handler_loud', 'Shout'),
        ('handler_memory', 'Item'),
        ('handler_responder', 'Trigger'),
        ('handler_sparkles', 'User'),
    ]:
        Model = apps.get_model(*model_label)
        updated = Model.objects.filter(workspace__isnull=True).update(
            workspace=workspace
        )
        if updated:
            print(
                f'  [backfill_workspace] Stamped {updated} {model_label[0]}.{model_label[1]} rows'
            )


def no_op(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('slacker', '0005_add_workspace_fk'),
        ('handler_about', '0002_add_workspace_fk'),
        ('handler_loud', '0003_add_workspace_fk'),
        ('handler_memory', '0003_add_workspace_fk'),
        ('handler_responder', '0003_add_workspace_fk'),
        ('handler_sparkles', '0004_add_workspace_fk'),
    ]

    operations = [migrations.RunPython(backfill, no_op)]
