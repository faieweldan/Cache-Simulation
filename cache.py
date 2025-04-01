from collections import deque, OrderedDict
from utils import Level


class CacheLevel(Level):
    def __init__(self, size, block_size, associativity, eviction_policy, write_policy, level_name, higher_level=None, lower_level=None):
        super().__init__(level_name, higher_level, lower_level)
        self.size = size
        self.block_size = block_size
        self.associativity = associativity
        self.eviction_policy = eviction_policy  # FIFO | LRU | MRU
        self.write_policy = write_policy  # always WB for this assignment

        # Number of cache sets = cache size / (block size * associativity)
        self.num_sets = self.size // (self.block_size * self.associativity)
        
        # Each set stores tag → dirty_bit (True/False)
        self.sets = [{} for _ in range(self.num_sets)]
        
        # Track eviction order
        if self.eviction_policy == "FIFO":
            self.eviction_tracker = [deque() for _ in range(self.num_sets)]
        else:  # LRU or MRU use OrderedDict
            self.eviction_tracker = [OrderedDict() for _ in range(self.num_sets)]

    def _calculate_index(self, address):
        block_number = address // self.block_size
        return block_number % self.num_sets

    def _calculate_tag(self, address):
        block_number = address // self.block_size
        return block_number // self.num_sets

    def _calculate_block_address(self, address):
        return address // self.block_size

    def _calculate_block_address_from_tag_index(self, tag, cache_index):
        return (tag * self.num_sets + cache_index) * self.block_size

    def is_dirty(self, block_address):
        cache_index = self._calculate_index(block_address * self.block_size)
        tag = self._calculate_tag(block_address * self.block_size)
        return self.sets[cache_index].get(tag, False)  # Default to False if tag not found

    def access(self, operation, address):
        cache_index = self._calculate_index(address)
        tag = self._calculate_tag(address)
        block_address = self._calculate_block_address(address)

        # Handle "B" operation (block writeback)
        if operation == "B":
            self.sets[cache_index][tag] = True  # Always dirty
            if self.eviction_policy in ["LRU", "MRU"]:
                self.eviction_tracker[cache_index][tag] = None
            elif self.eviction_policy == "FIFO":
                self.eviction_tracker[cache_index].append(tag)
            return

        # Check if the block is in the cache (hit or miss)
        if tag in self.sets[cache_index]:
            # Cache hit
            self.report_hit(operation, address)
            if operation == "W":  # Write operation
                self.sets[cache_index][tag] = True  # Set dirty bit
            # Update eviction policy
            if self.eviction_policy in ["LRU", "MRU"]:
                self.eviction_tracker[cache_index].move_to_end(tag, last=(self.eviction_policy == "LRU"))
        else:
            # Cache miss
            self.report_miss(operation, address)
            if len(self.sets[cache_index]) >= self.associativity:
                # Evict a block if necessary
                self.evict(cache_index)
            # Allocate space for the new block
            self.sets[cache_index][tag] = (operation == "W")  # Set dirty bit if write
            if self.eviction_policy in ["LRU", "MRU"]:
                self.eviction_tracker[cache_index][tag] = None
            elif self.eviction_policy == "FIFO":
                self.eviction_tracker[cache_index].append(tag)
            # Fetch block from higher level if available
            if self.higher_level:
                self.higher_level.access("R", address)

    def evict(self, cache_index):
        if self.eviction_policy == "FIFO":
            victim_tag = self.eviction_tracker[cache_index].popleft()
        elif self.eviction_policy == "LRU":
            victim_tag = next(iter(self.eviction_tracker[cache_index]))
        elif self.eviction_policy == "MRU":
            victim_tag = next(reversed(self.eviction_tracker[cache_index]))

        # Remove the block from the set
        block_address = self._calculate_block_address_from_tag_index(victim_tag, cache_index)
        if self.sets[cache_index][victim_tag]:  # If dirty, perform writeback
            self.report_writeback(block_address)
            if self.lower_level:
                self.lower_level.access("B", block_address * self.block_size)
        del self.sets[cache_index][victim_tag]
        self.report_eviction(block_address)

    def invalidate(self, block_address):
        cache_index = self._calculate_index(block_address * self.block_size)
        tag = self._calculate_tag(block_address * self.block_size)

        if tag in self.sets[cache_index]:
            # Check if the block is dirty
            if self.sets[cache_index][tag]:
                # Perform writeback if dirty
                self.report_writeback(block_address)
                if self.lower_level:
                    self.lower_level.access("B", block_address * self.block_size)
            # Remove the block
            del self.sets[cache_index][tag]
            if self.eviction_policy in ["LRU", "MRU"]:
                del self.eviction_tracker[cache_index][tag]
            elif self.eviction_policy == "FIFO":
                self.eviction_tracker[cache_index].remove(tag)
            self.report_eviction(block_address)