from datetime import datetime, timezone
from logging import getLogger
from typing import Optional

from slack_sdk.oauth.installation_store import InstallationStore
from slack_sdk.oauth.installation_store.models.bot import Bot
from slack_sdk.oauth.installation_store.models.installation import Installation

log = getLogger('DjangoInstallationStore')


class DjangoInstallationStore(InstallationStore):
    '''
    Bolt InstallationStore backed by the slacker.Workspace Django model.

    We only need to persist bot-level installs (no user-token OAuth), so
    find_installation delegates to find_bot, and delete_installation delegates
    to delete_bot.
    '''

    # Import here to avoid circular imports at module load time (this module
    # is imported during app init, before Django apps are fully ready).
    @staticmethod
    def _model():
        from slacker.models import Workspace

        return Workspace

    def save(self, installation: Installation):
        Workspace = self._model()
        scopes = ','.join(installation.bot_scopes or [])
        installed_at = (
            datetime.fromtimestamp(installation.installed_at, tz=timezone.utc)
            if installation.installed_at
            else datetime.now(tz=timezone.utc)
        )
        Workspace.objects.update_or_create(
            team_id=installation.team_id,
            defaults={
                'team_name': installation.team_name or '',
                'enterprise_id': installation.enterprise_id or None,
                'bot_token': installation.bot_token or '',
                'bot_id': installation.bot_id or '',
                'bot_user_id': installation.bot_user_id or '',
                'bot_scopes': scopes,
                'installed_at': installed_at,
            },
        )
        log.info(
            'save: team_id=%s, team_name=%s',
            installation.team_id,
            installation.team_name,
        )

    def find_bot(
        self,
        *,
        enterprise_id: Optional[str],
        team_id: Optional[str],
        is_enterprise_install: Optional[bool] = False,
    ) -> Optional[Bot]:
        Workspace = self._model()
        try:
            ws = Workspace.objects.get(team_id=team_id)
        except Workspace.DoesNotExist:
            log.debug('find_bot: not found, team_id=%s', team_id)
            return None

        installed_at = ws.installed_at.timestamp() if ws.installed_at else None
        bot = Bot(
            team_id=ws.team_id,
            team_name=ws.team_name,
            enterprise_id=ws.enterprise_id,
            is_enterprise_install=bool(ws.enterprise_id),
            bot_token=ws.bot_token,
            bot_id=ws.bot_id,
            bot_user_id=ws.bot_user_id,
            bot_scopes=ws.bot_scopes.split(',') if ws.bot_scopes else [],
            installed_at=installed_at,
        )
        log.debug('find_bot: found team_id=%s', team_id)
        return bot

    def find_installation(
        self,
        *,
        enterprise_id: Optional[str],
        team_id: Optional[str],
        user_id: Optional[str] = None,
        is_enterprise_install: Optional[bool] = False,
    ) -> Optional[Installation]:
        # We only store bot-level installs; synthesise an Installation from bot data.
        bot = self.find_bot(
            enterprise_id=enterprise_id,
            team_id=team_id,
            is_enterprise_install=is_enterprise_install,
        )
        if bot is None:
            return None
        return Installation(
            team_id=bot.team_id,
            team_name=bot.team_name,
            enterprise_id=bot.enterprise_id,
            is_enterprise_install=bot.is_enterprise_install,
            bot_token=bot.bot_token,
            bot_id=bot.bot_id,
            bot_user_id=bot.bot_user_id,
            bot_scopes=bot.bot_scopes,
            installed_at=bot.installed_at,
            # No user token in this bot-only install flow.
            user_id=user_id,
        )

    def delete_bot(
        self, *, enterprise_id: Optional[str], team_id: Optional[str]
    ):
        Workspace = self._model()
        _, deleted_by_model = Workspace.objects.filter(team_id=team_id).delete()
        log.info(
            'delete_bot: team_id=%s, deleted=%s', team_id, deleted_by_model
        )

    def delete_installation(
        self,
        *,
        enterprise_id: Optional[str],
        team_id: Optional[str],
        user_id: Optional[str] = None,
    ):
        self.delete_bot(enterprise_id=enterprise_id, team_id=team_id)
