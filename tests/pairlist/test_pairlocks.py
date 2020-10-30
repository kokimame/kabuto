from datetime import datetime, timedelta, timezone

import arrow
import pytest

from freqtrade.persistence import PairLocks
from freqtrade.persistence.models import PairLock


@pytest.mark.parametrize('use_db', (False, True))
@pytest.mark.usefixtures("init_persistence")
def test_PairLocks(use_db):
    PairLocks.timeframe = '5m'
    # No lock should be present
    if use_db:
        assert len(PairLock.query.all()) == 0
    else:
        PairLocks.use_db = False

    assert PairLocks.use_db == use_db

    pair = 'ETH/BTC'
    assert not PairLocks.is_pair_locked(pair)
    PairLocks.lock_pair(pair, arrow.utcnow().shift(minutes=4).datetime)
    # ETH/BTC locked for 4 minutes
    assert PairLocks.is_pair_locked(pair)

    # XRP/BTC should not be locked now
    pair = 'XRP/BTC'
    assert not PairLocks.is_pair_locked(pair)
    # Unlocking a pair that's not locked should not raise an error
    PairLocks.unlock_pair(pair)

    PairLocks.lock_pair(pair, arrow.utcnow().shift(minutes=4).datetime)
    assert PairLocks.is_pair_locked(pair)

    # Get both locks from above
    locks = PairLocks.get_pair_locks(None)
    assert len(locks) == 2

    # Unlock original pair
    pair = 'ETH/BTC'
    PairLocks.unlock_pair(pair)
    assert not PairLocks.is_pair_locked(pair)
    assert not PairLocks.is_global_lock()

    pair = 'BTC/USDT'
    # Lock until 14:30
    lock_time = datetime(2020, 5, 1, 14, 30, 0, tzinfo=timezone.utc)
    PairLocks.lock_pair(pair, lock_time)

    assert not PairLocks.is_pair_locked(pair)
    assert PairLocks.is_pair_locked(pair, lock_time + timedelta(minutes=-10))
    assert not PairLocks.is_global_lock(lock_time + timedelta(minutes=-10))
    assert PairLocks.is_pair_locked(pair, lock_time + timedelta(minutes=-50))
    assert not PairLocks.is_global_lock(lock_time + timedelta(minutes=-50))

    # Should not be locked after time expired
    assert not PairLocks.is_pair_locked(pair, lock_time + timedelta(minutes=10))

    locks = PairLocks.get_pair_locks(pair, lock_time + timedelta(minutes=-2))
    assert len(locks) == 1
    assert 'PairLock' in str(locks[0])

    # Unlock all
    PairLocks.unlock_pair(pair, lock_time + timedelta(minutes=-2))
    assert not PairLocks.is_global_lock(lock_time + timedelta(minutes=-50))

    # Global lock
    PairLocks.lock_pair('*', lock_time)
    assert PairLocks.is_global_lock(lock_time + timedelta(minutes=-50))
    # Global lock also locks every pair seperately
    assert PairLocks.is_pair_locked(pair, lock_time + timedelta(minutes=-50))
    assert PairLocks.is_pair_locked('XRP/USDT', lock_time + timedelta(minutes=-50))

    if use_db:
        assert len(PairLock.query.all()) > 0
    else:
        # Nothing was pushed to the database
        assert len(PairLock.query.all()) == 0
    # Reset use-db variable
    PairLocks.use_db = True
