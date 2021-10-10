from django.db import models


class Channel(models.Model):
    '''
    https://api.slack.com/methods/conversations.info
    {
        "ok": true,
        "channel": {
            "id": "C012AB3CD",
            "name": "general",
            "is_channel": true,
            "is_group": false,
            "is_im": false,
            "created": 1449252889,
            "creator": "W012A3BCD",
            "is_archived": false,
            "is_general": true,
            "unlinked": 0,
            "name_normalized": "general",
            "is_read_only": false,
            "is_shared": false,
            "parent_conversation": null,
            "is_ext_shared": false,
            "is_org_shared": false,
            "pending_shared": [],
            "is_pending_ext_shared": false,
            "is_member": true,
            "is_private": false,
            "is_mpim": false,
            "last_read": "1502126650.228446",
            "topic": {
                "value": "For public discussion of generalities",
                "creator": "W012A3BCD",
                "last_set": 1449709364
            },
            "purpose": {
                "value": "This part of the workspace is for fun. Make fun here.",
                "creator": "W012A3BCD",
                "last_set": 1449709364
            },
            "previous_names": [
                "specifics",
                "abstractions",
                "etc"
            ],
            "locale": "en-US"
        }
    }
    '''

    class Type(models.TextChoices):
        PUBLIC = 'private'
        PRIVATE = 'public'
        DIRECT = 'direct'

        @classmethod
        def lookup(cls, val):
            return {
                'C': cls.PUBLIC,
                'G': cls.PRIVATE,
                'channel': cls.PUBLIC,
                'group': cls.PRIVATE,
                'im': cls.DIRECT,
            }[val]

    id = models.CharField(max_length=16, primary_key=True)
    team_id = models.CharField(max_length=16)
    name = models.CharField(max_length=255)
    channel_type = models.CharField(max_length=7, choices=Type.choices)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('team_id', 'name'),)
