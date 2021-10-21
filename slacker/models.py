from django.db import models

from simone.context import ChannelType


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
        PUBLIC = 'public'
        PRIVATE = 'private'
        DIRECT = 'direct'

    id = models.CharField(max_length=16, primary_key=True)
    name = models.CharField(max_length=255)
    channel_type = models.CharField(max_length=7, choices=Type.choices)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def channel_type_enum(self):
        if isinstance(self.channel_type, ChannelType):
            return self.channel_type
        if self.channel_type == 'public':
            return ChannelType.PUBLIC
        elif self.channel_type == 'private':
            return ChannelType.PRIVATE
        return ChannelType.DIRECT
