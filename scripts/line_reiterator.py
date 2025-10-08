from dataclasses import dataclass, field
from typing import Literal
from collections.abc import Iterable, Iterator

EndType = type('EndType', (), {})
End = EndType()
EndType.__new__ = lambda _, *__, **___: End

@dataclass
class LineReiterator:
    _iter:  Iterator
    _index: int
    _line:  str | EndType
    # _exhausted: bool

    def __init__(self, it: Iterable | Iterator):
        self._iter = iter(it)
        self._index = 0
        # self._exhausted = False
        try:
            self._line = next(self._iter)
        except StopIteration:
            # self._exhausted = True
            self._line = End

    def __iter__(self):
        return self

    def __next__(self):
        if self._line is End:
            raise StopIteration
        r = self._line
        try:
            self._line = next(self._iter)
        except StopIteration:
            self._exhausted = True
            self._line = End
        self._index += 1
        return r

    @property
    def line(self):
        return self._line

    def __call__(self):
        return self.line

    @property
    def index(self):
        return self._index

    @property
    def line_no(self):
        return self._index + 1
