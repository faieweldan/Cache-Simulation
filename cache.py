from collections import deque, OrderedDict
from utils import Level

class CacheLevel(Level):
    def __init__(self, size, block_size, associativity, eviction_policy, write_policy, level_name, higher_level=None, lower_level=None):
        super().__init__(level_name, higher_level, lower_level)
        # Setting up cache variables.
        self.cache_size = size  # Total size of cache.
        self.block_size = block_size  # Size of each block in cache.
        self.associativity = associativity  # Number of blocks in each cache set.
        self.eviction_policy = eviction_policy.upper()  # Eviction policy, can be FIFO, LRU, or MRU.
        self.write_policy = write_policy.upper()  # Write policy, usually write-back (WB).

        # Calculate how many sets we have in the cache based on size and associativity.
        self.num_sets = self.cache_size // (self.block_size * self.associativity)
        self.offset_bits = self.block_size.bit_length() - 1  # Number of bits for the block offset.
        self.index_bits = self.num_sets.bit_length() - 1  # Number of bits for the index.

        # We have a list of ordered dictionaries, one for each cache set.
        self.cache = [OrderedDict() for _ in range(self.num_sets)]
        # This holds the dirty bits for each block. Metadata!
        self.cache_metadata = [{} for _ in range(self.num_sets)]

    def _calculate_index(self, address):
        # This is to calculate which cache set the block will go to.
        return (address >> self.offset_bits) & (self.num_sets - 1)

    def _calculate_tag(self, address):
        # This calculates the tag for a given block, used to identify the block in cache.
        return address >> (self.index_bits + self.offset_bits)

    def _calculate_block_address(self, address):
        # Align the address to the start of the block.
        return address & ~(self.block_size - 1)

    def _calculate_block_address_from_tag_index(self, tag, cache_index):
        # Given a tag and cache set index, calculate the actual block address.
        return (tag << (self.index_bits + self.offset_bits)) | (cache_index << self.offset_bits)

    def is_dirty(self, block_address):
        # This checks if the block is dirty (modified) in the cache.
        cache_index = self._calculate_index(block_address)
        tag = self._calculate_tag(block_address)
        return self.cache_metadata[cache_index].get(tag, {}).get("dirty", False)

    def access(self, operation, address):
        """
        operation: 'R' for Read, 'W' for Write
        What happens here is that we check if the block is in the cache. 
        If not, we fetch it and maybe evict something!
        """
        block_addr = self._calculate_block_address(address)  # Align address to the block
        cache_index = self._calculate_index(block_addr)  # Find out which cache set it goes to
        tag = self._calculate_tag(block_addr)  # Get the tag for the block

        # Check if the block is already in the cache.
        if tag in self.cache[cache_index]:
            self.report_hit(operation, address)  # It's a hit! We found it in the cache.
            if operation == 'W':
                self.cache_metadata[cache_index][tag]["dirty"] = True  # Mark it dirty if it's a write.
            self._update_recency(cache_index, tag)  # Update recency based on eviction policy.
        else:
            self.report_miss(operation, address)  # Cache miss! We didn't find it.
            # If the cache set is full, we need to evict a block.
            if len(self.cache[cache_index]) >= self.associativity:
                self.evict(cache_index)
            # If it's a write miss, we need to fetch the block as a read first.
            prop_operation = operation if self.lower_level else 'R'
            if self.higher_level:
                self.higher_level.access(prop_operation, block_addr)
            # Insert the block into the cache and mark it dirty if it's a write.
            self.cache[cache_index][tag] = None
            self.cache_metadata[cache_index][tag] = {"dirty": (operation == 'W')}

    def evict(self, cache_index):
        """
        Eviction policy time! We need to evict a block according to the FIFO, LRU, or MRU policy.
        If the block is dirty, we write it back to memory.
        """
        if not self.cache[cache_index]:
            return  # Nothing to evict, it's empty.

        # Decide which block to evict based on the eviction policy.
        victim_block_tag = None
        if self.eviction_policy == "FIFO":
            victim_block_tag = next(iter(self.cache[cache_index]))  # First block in cache (FIFO).
        elif self.eviction_policy == "LRU":
            victim_block_tag = next(iter(self.cache[cache_index]))  # Least recently used block.
        elif self.eviction_policy == "MRU":
            victim_block_tag = next(reversed(self.cache[cache_index]))  # Most recently used block.

        # Calculate the block address of the victim that we need to evict.
        evicted_block_address = self._calculate_block_address_from_tag_index(victim_block_tag, cache_index)
        self.invalidate(evicted_block_address)

    def invalidate(self, block_address):
        """
        This removes a block from the cache. If it's dirty, it writes the block back to memory.
        """
        cache_index = self._calculate_index(block_address)  # Find the cache set
        tag = self._calculate_tag(block_address)  # Get the tag of the block

        if tag not in self.cache[cache_index]:
            return  # If the block isn't in the cache, nothing to invalidate.

        # If the block is dirty, we need to write it back to memory (lower level).
        if self.cache_metadata[cache_index][tag]["dirty"]:
            self.report_writeback(block_address)
            if self.higher_level:
                self.higher_level.access('W', block_address)

        # Actually remove the block from cache and metadata.
        del self.cache[cache_index][tag]
        del self.cache_metadata[cache_index][tag]
        self.report_eviction(block_address)  # Report that we evicted the block.

    def _update_recency(self, cache_index, tag):
        """
        This function updates the recency of a block depending on the eviction policy:
        - For LRU: Move the block to the end (most recently used).
        - For MRU: Move the block to the front (most recently used).
        - FIFO: Do nothing, we don't care about the order.
        """
        if self.eviction_policy == "LRU":
            self.cache[cache_index].move_to_end(tag)  # Move to end to mark as recently used.
        elif self.eviction_policy == "MRU":
            self.cache[cache_index].move_to_end(tag, last=False)  # Move to front to mark as most recently used.
        # FIFO doesn't need to do anything, just keep the order.
