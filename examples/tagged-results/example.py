"""Use a dataclass field to round-trip flat tagged results with dataclass-wizard 1.0.0."""

from dataclasses import asdict as plain_asdict, dataclass
import json

import dataclass_wizard as dw
from dataclass_wizard import LoadMeta


@dataclass
class ResErr:
    item_id: str
    msg: str


@dataclass
class ResOk:
    item_id: str
    item: str


Res = ResErr | ResOk

LoadMeta(tag='ResErr').bind_to(ResErr)
LoadMeta(tag='ResOk').bind_to(ResOk)


@dataclass
class Container:
    res: Res


def main() -> None:
    results = [ResErr(item_id='Q0001', msg='err'), ResOk(item_id='Q0002', item='ok')]
    for iteration in (1, 2):
        for result in results:
            # The union is a dataclass field; only its flat value goes on the wire.
            wire = dw.asdict(Container(res=result))['res']
            received = json.loads(json.dumps(wire))
            restored = dw.fromdict(Container, {'res': received}).res
            print(json.dumps({
                'round': iteration,
                'wire': wire,
                'restored_type': type(restored).__name__,
                'restored': plain_asdict(restored),
            }, sort_keys=True))


if __name__ == '__main__':
    main()
