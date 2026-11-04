"""Invalidate legacy broad plaintext tokens and remove retired configuration."""
import hashlib
import json
from app.core.database import session_scope
from app.models import Config, Token, Task


def migrate_access_tokens():
    with session_scope() as db:
        for token in db.query(Token).all():
            # New tokens store a SHA-256 digest; old keys intentionally lose access.
            if len(token.token_value) != 64 or any(c not in '0123456789abcdef' for c in token.token_value):
                token.token_value = hashlib.sha256(token.token_value.encode()).hexdigest()
                token.permissions = '[]'
                token.enabled = False
        db.query(Config).filter(Config.key.in_(['PageAgentConfig','TGBotConfig','DiscordBotConfig','WeComBotConfig'])).delete(synchronize_session=False)
        db.query(Task).filter(Task.task_func == 'check_version_update_and_notify').delete(synchronize_session=False)
