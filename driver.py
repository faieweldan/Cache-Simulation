#!/usr/bin/env python3

#
#  .d8888b.  888b     d888 8888888b.  8888888888 888b    888          d8888   .d8888b.   d888
# d88P  Y88b 8888b   d8888 888   Y88b 888        8888b   888         d8P888  d88P  Y88b d8888
# 888    888 88888b.d88888 888    888 888        88888b  888        d8P 888       .d88P   888
# 888        888Y88888P888 888   d88P 8888888    888Y88b 888       d8P  888      8888"    888
# 888        888 Y888P 888 8888888P"  888        888 Y88b888      d88   888       "Y8b.   888
# 888    888 888  Y8P  888 888        888        888  Y88888      8888888888 888    888   888
# Y88b  d88P 888   "   888 888        888        888   Y8888            888  Y88b  d88P   888
#  "Y8888P"  888       888 888        8888888888 888    Y888            888   "Y8888P"  8888888
#
#                        P2 - Cache Simulation | Sampson & Devic 2025


from utils import Level, Memory
from collections import deque
from cache import CacheLevel
import argparse
import sys

if __name__ == '__main__':
    parser = argparse.ArgumentParser("Cache Simulator")
    parser.add_argument(
        'config',
        type=argparse.FileType('r'),
        help='Path to the cache configuration file'
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-t', '--trace', type=argparse.FileType('r'),
                       help='Path to a specific trace file')
    group.add_argument('--stdin', action='store_true',
                       help='Read input traces from stdin')

    args = parser.parse_args()

    # define the memory hierarchy
    memory_hierarchy = deque()  # type: deque[Level]
    # last level in the hierarchy is memory, always hits
    memory_hierarchy.append(Memory())

    # parse the levels of the memory hierarchy
    # get how many levels there are
    num_levels = int(args.config.readline().strip())
    # for each level, parse the level parameters
    for _ in range(num_levels):
        # get the metadata
        c_size, c_block, c_assoc, epolicy, wpolicy, name = args.config.readline().strip().split(',')
        # set the new lowest level of the hierarchy
        new_level = CacheLevel(
            int(c_size),
            int(c_block),
            int(c_assoc),
            epolicy,
            wpolicy,
            name,
            memory_hierarchy[0],
            None
        )
        memory_hierarchy[0].lower_level = new_level
        memory_hierarchy.appendleft(new_level)

    print('Memory Hierarchy:')
    print('\t' + ' <-> '.join([level.name for level in memory_hierarchy]))

    # now that the hierarchy is defined, perform the R/W accesses on the cache
    for idx, mem_access in enumerate(sys.stdin if args.stdin else args.trace):
        a_type, a_addr = mem_access.strip().split(',')
        if a_type not in {'R', 'W'}: raise ValueError(f'Invalid memory access type found at line {idx}: {a_type}')
        memory_hierarchy[0].access(a_type, int(a_addr, 16))

    # after the test is done report overall stats
    for mem_level in memory_hierarchy:
        mem_level.report_statistics()
