import logging
from typing import Any, Dict, Optional
from pathlib import Path


logger = logging.getLogger(__name__)


def create_datadir(config: Dict[str, Any], datadir: Optional[str] = None) -> str:

    folder = Path(datadir) if datadir else Path('user_data/data')
    if not datadir:
        # set datadir
        exchange_name = config.get('exchange', {}).get('name').lower()
        folder = folder.joinpath(exchange_name)

    if not folder.is_dir():
        folder.mkdir(parents=True)
        logger.info(f'Created data directory: {datadir}')
    return str(folder)
