from collections import OrderedDict
from utils import Level  # base Level class

class CacheLevel(Level):
    """
    This is a write-back, write-allocate cache that uses FIFO, LRU, or MRU for eviction.
    It supports connecting to higher and lower cache levels for simulation.
    """

    def __init__(self, size, block_size, associativity,
                 eviction_policy, write_policy,
                 level_name, higher_level=None, lower_level=None):
        # This function sets up the cache size, block size, associativity, eviction policy, and connections.
        super().__init__(level_name, higher_level, lower_level)
        self.size = size
        self.block_size = block_size
        self.associativity = associativity
        self.eviction_policy = eviction_policy.upper()
        self.write_policy = write_policy.upper()

        self.num_sets = self.size // (self.block_size * self.associativity)
        self.offsets = (self.block_size).bit_length() - 1
        self.index = (self.num_sets).bit_length() - 1

        # One OrderedDict for each set, keeping blocks with tags and dirty info
        self.cache = [OrderedDict() for _ in range(self.num_sets)]

    def _calc_index(self, address: int) -> int:
        # This function gets the cache set index from the address.
        return (address >> self.offsets) & (self.num_sets - 1)

    def _calc_tag(self, address: int) -> int:
        # This function gets the tag from the address.
        return address >> (self.index + self.offsets)

    def _block_align(self, address: int) -> int:
        # This function removes the offset bits to get the block-aligned address.
        return address & ~(self.block_size - 1)

    def _addr_from_tag_index(self, tag: int, set_index: int) -> int:
        # This function reconstructs the block address from tag and index.
        return (tag << (self.index + self.offsets)) | (set_index << self.offsets)

    def is_dirty(self, address):
        # This function checks if the block at the given address is marked dirty.
        block_addr = self._block_align(address)
        set_index = self._calc_index(block_addr)
        tag = self._calc_tag(block_addr)
        block_info = self.cache[set_index].get(tag)
        return block_info["dirty"] if block_info else False

    def has_block(self, address: int) -> bool:
        # This function checks if the block exists in the cache.
        block_addr = self._block_align(address)
        set_index = self._calc_index(block_addr)
        tag = self._calc_tag(block_addr)
        return tag in self.cache[set_index]

    def _update_recency(self, set_index, tag):
        # This function updates the usage order of a block for LRU or MRU.
        self.cache[set_index].move_to_end(tag)

    def _select_victim_tag(self, set_index) -> int:
        # This function chooses which block to evict based on the policy.
        if not self.cache[set_index]:
            return None
        if self.eviction_policy in ("FIFO", "LRU"):
            return next(iter(self.cache[set_index]))  # oldest one
        elif self.eviction_policy == "MRU":
            return next(reversed(self.cache[set_index]))  # newest one

    def access(self, operation, address):
        """
        This function handles access to the cache:
        'R' = read, 'W' = write, 'B' = write-back (dirty block).
        """
        block_addr = self._block_align(address)
        set_index = self._calc_index(block_addr)
        tag = self._calc_tag(block_addr)

        # Handle write-back (B) first
        if operation == 'B':
            if tag not in self.cache[set_index]:
                self.cache[set_index][tag] = {"dirty": True}
            else:
                self.cache[set_index][tag]["dirty"] = True
            self.report_hit("B", address)
            return

        # Handle hit case
        if tag in self.cache[set_index]:
            self.report_hit(operation, address)
            if operation == 'W' and self.lower_level is None:
                self.cache[set_index][tag]["dirty"] = True
            if self.eviction_policy in ("LRU", "MRU"):
                self._update_recency(set_index, tag)
        # Handle miss case
        else:
            self.report_miss(operation, address)

            # Evict if the set is full
            if len(self.cache[set_index]) >= self.associativity:
                self.evict(set_index)

            # Ask the higher level to get the block
            if self.higher_level:
                self.higher_level.access('R', address)

            # Add the block to cache
            self.cache[set_index][tag] = {"dirty": False}

            # Set dirty if it's a write and no lower level
            if self.lower_level is None:
                if operation == 'W':
                    self.cache[set_index][tag]["dirty"] = True
            else:
                # If lower level has dirty block, mark this one dirty too
                if self.lower_level.has_block(block_addr) and self.lower_level.is_dirty(block_addr):
                    self.cache[set_index][tag]["dirty"] = True

    def evict(self, set_index):
        # This function removes a block from a full set based on the eviction policy.
        victim_tag = self._select_victim_tag(set_index)
        if victim_tag is None:
            return
        victim_addr = self._addr_from_tag_index(victim_tag, set_index)

        # Invalidate in lower level first (if inclusive)
        if self.lower_level and self.lower_level.has_block(victim_addr):
            self.lower_level.invalidate(victim_addr, skip_lower_levels=False)

        # Then remove from this cache
        self.invalidate(victim_addr, skip_lower_levels=True)

    def invalidate(self, address, skip_lower_levels=False):
        # This function deletes a block from cache, and writes it back if dirty.
        block_addr = self._block_align(address)
        set_index = self._calc_index(block_addr)
        tag = self._calc_tag(block_addr)

        block_info = self.cache[set_index].get(tag)
        if block_info is None:
            return

        # Critical: first handle dirty data and do writeback before eviction reporting
        if block_info["dirty"]:
            self.report_writeback(block_addr)
            if self.higher_level:
                self.higher_level.access('B', block_addr)
            block_info["dirty"] = False

        # Only after writeback, remove block and report eviction
        del self.cache[set_index][tag]
        self.report_eviction(block_addr)

        # Handle invalidation in lower levels if needed
        if not skip_lower_levels and self.lower_level:
            self.lower_level.invalidate(block_addr, skip_lower_levels=False)