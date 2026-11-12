"""Preserve one string parameter while other values use Fire's normal parsing."""

import json

import fire
from fire import decorators


@decorators.SetParseFns(arg=str)
def main(arg: str, count: int):
    print(json.dumps({
        "arg": arg,
        "arg_type": type(arg).__name__,
        "count": count,
        "count_type": type(count).__name__,
    }))


if __name__ == "__main__":
    fire.Fire(main)
