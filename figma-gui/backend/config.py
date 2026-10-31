"""Configuration is read from figma-gui/.env, never embedded in frontend code."""
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')

@dataclass(frozen=True)
class Settings:
    database_url: str
    secret: str
    secure: bool = True
    origins: tuple[str, ...] = ('http://localhost:5173', 'http://127.0.0.1:5173')
    mode: str = 'SIMULATION'
    minutes: int = 30
    backup_dir: Path = ROOT / 'backups'

    @classmethod
    def from_env(cls):
        secret = os.getenv('AUTH_SECRET', '')
        if len(secret) < 32 or secret.startswith('REPLACE_'):
            raise RuntimeError('Set AUTH_SECRET to a random secret of at least 32 characters in figma-gui/.env.')
        url = os.getenv('DATABASE_URL', '')
        if not url:
            raise RuntimeError('DATABASE_URL is required; PostgreSQL must be running.')
        mode = os.getenv('TELEMETRY_MODE', 'SIMULATION').upper()
        if mode not in ('SIMULATION', 'DATABASE'):
            raise RuntimeError('TELEMETRY_MODE must be SIMULATION or DATABASE.')
        minutes = int(os.getenv('SESSION_MINUTES', '30'))
        if not 1 <= minutes <= 120:
            raise RuntimeError('SESSION_MINUTES must be between 1 and 120.')
        backup = Path(os.getenv('BACKUP_DIR', 'backups'))
        return cls(url, secret, os.getenv('COOKIE_SECURE', 'true').lower() == 'true',
                   tuple(s.strip() for s in os.getenv('ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',') if s.strip()),
                   mode, minutes, backup if backup.is_absolute() else ROOT / backup)
