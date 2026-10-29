from datetime import UTC, datetime

import time_machine
from freezegun import freeze_time

time_machine.naive_mode = time_machine.NaiveMode.ERROR


@time_machine.travel("2025-12-11T12:01:02Z", tick=False)
def test_time_machine() -> None:
    assert datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S.%f") == '2025-12-11 12:01:02.000000'
    assert datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S.%f") == '2025-12-11 12:01:02.000000'


@freeze_time("2025-12-11T12:01:02Z")
def test_freezegun() -> None:
    assert datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S.%f") == '2025-12-11 12:01:02.000000'
    assert datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S.%f") == '2025-12-11 12:01:02.000000'
