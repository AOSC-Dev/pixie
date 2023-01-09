# -*- coding: utf-8 -*-

from os import walk
from typing import Iterable
from pathlib import Path

ELF_MAGIC: bytes = b'\x7fELF'


def is_elf(path: Path) -> bool:
    if path.is_dir():
        return False
    magic: bytes = bytes()
    with open(path, 'rb') as f:
        magic = f.read(4)
    return magic == ELF_MAGIC


def find_elfs(path: Path) -> Iterable[Path]:
    if path.is_file():
        if is_elf(path):
            yield path
        return None
    for (root, _, files) in walk(path):
        dir = Path(root)
        for file in files:
            path = dir / file
            if is_elf(path):
                yield path
