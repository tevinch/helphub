"""A four-part return value documented in NumPy style."""

from typing import Any


def f(data: dict[str, Any]) -> tuple[
    dict[str, list[int]],
    dict[str, list[int]],
    dict[str, dict[str, list[int]]],
    dict[str, dict[str, list[int]]],
]:
    """Return four related collections.

    Parameters
    ----------
    data : dict[str, Any]
        The input data.

    Returns
    -------
    first : dict[str, list[int]]
        This is a long description of the result that is wrapped onto
        another line without changing the return value's meaning.
    second : dict[str, list[int]]
        The second collection.
    third : dict[str, dict[str, list[int]]]
        The third collection.
    fourth : dict[str, dict[str, list[int]]]
        The fourth collection.
    """
    return (
        {"first": [1]},
        {"second": [2]},
        {"third": {"inner": [3]}},
        {"fourth": {"inner": [4]}},
    )
