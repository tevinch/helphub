"""A minimal Python Fire command with a version-like string argument."""

import fire
from fire import decorators


@decorators.SetParseFns(arg=str)
def main(arg: str):
    print(f"Hello! {type(arg)} {arg}")


if __name__ == "__main__":
    fire.Fire(main)

