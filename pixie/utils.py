# -*- coding: utf-8 -*-

# This modifies the behavior of input() without any direct invocation
import readline  # type: ignore # noqa: F401

from typing import Optional, Callable, Set
from logging import Formatter, LogRecord, DEBUG, INFO, WARN, ERROR

# For .contents and .readelf
CONTENTS_REGEX_TEMPLATE: str = 'usr/lib/{}\\.so(\\.[0-9]+)*[ \t]+'

# For to_pkgdep
MAX_CHARS_PER_LINE: int = 80
PKGDEP_PREFIX: str = 'PKGDEP="'
PKGDEP_LINEBREAK: str = '\\'
PKGDEP_SEPARATOR: str = ' '
PKGDEP_SUFFIX: str = '"'


class Colors(object):
    RED = '\033[31m'
    YELLOW = '\033[33m'
    BRIGHT_BLACK = '\033[90m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


PROMPT_PREFIX: str = f' {Colors.YELLOW}?{Colors.RESET}{Colors.BOLD} '
PROMPT_FINISHED_PREFIX: str = f' {Colors.GREEN}✔{Colors.RESET}{Colors.BOLD} '
PROMPT_SUFFIX: str = f' {Colors.RESET}{Colors.BRIGHT_BLACK}›{Colors.RESET} '
PROMPT_FINISHED_SUFFIX: str = \
    f' {Colors.RESET}{Colors.BRIGHT_BLACK}·{Colors.RESET} '
PROMPT_DEFAULT_PREFIX: str = f' {Colors.RESET}{Colors.BRIGHT_BLACK}('
PROMPT_DEFAULT_SUFFIX: str = f'){Colors.RESET}'
UP: str = '\033[1A'
CLEAR: str = '\033[2K'
HIDE_CURSOR: str = '\033[?25l'
SHOW_CURSOR: str = '\033[?25h'


class ColorfulTheme(Formatter):
    fmt_prefix = f'{Colors.RESET}{Colors.BOLD}[{Colors.RESET}'
    fmt_suffix = f'%(levelname)s{Colors.RESET}{Colors.BOLD}] %(message)s'

    COLORS = {
        INFO: Colors.BLUE,
        DEBUG: Colors.YELLOW,
        WARN: Colors.CYAN,
        ERROR: Colors.RED,
    }

    def format(self, record: LogRecord) -> str:
        log_color = self.COLORS.get(record.levelno) or ''
        formatter = Formatter(
            self.fmt_prefix + log_color + self.fmt_suffix + Colors.RESET)
        return formatter.format(record)


def read_line(
    prompt: str = 'Input',
    default: Optional[str] = None,
    verify: Callable[[str], bool] = lambda _: True
) -> str:
    prompt_default = ''
    default_content = default or ''
    if default is not None:
        prompt_default = \
            f'{PROMPT_DEFAULT_PREFIX}{default}{PROMPT_DEFAULT_SUFFIX}'
    full_prompt = f'{PROMPT_PREFIX}{prompt}{prompt_default}{PROMPT_SUFFIX}'
    ret = input(full_prompt) or default_content
    while not verify(ret):
        ret = input(f'{UP}{CLEAR}{full_prompt}') or default_content
    print(f'{UP}{CLEAR}{PROMPT_FINISHED_PREFIX}{prompt}\
{PROMPT_FINISHED_SUFFIX}{Colors.GREEN}{ret}{Colors.RESET}')
    return ret


def to_pkgdep(packages: Set[str]) -> str:
    if len(packages) < 1:
        return PKGDEP_PREFIX + PKGDEP_SUFFIX

    pkgs = [f'{pkg} ' for pkg in packages]
    pkgs.sort()
    ret = PKGDEP_PREFIX
    prefix_len = len(ret)
    line_len = 0
    break_len = len(PKGDEP_LINEBREAK)
    line_pre = PKGDEP_LINEBREAK + '\n' + ' ' * prefix_len
    max_line_len = MAX_CHARS_PER_LINE - prefix_len - break_len
    for pkg in pkgs:
        pkg_len = len(pkg)
        if (line_len + pkg_len) <= max_line_len:
            ret += pkg
            line_len += pkg_len
            continue
        # Add line break
        line_len = pkg_len
        ret += line_pre + pkg
    return ret[:-1] + PKGDEP_SUFFIX
