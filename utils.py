# Do not edit anything in here, your changes will not be accepted/submitted

class Level:
    """
    Defines an abstract memory hierarchy level
    """
    def __init__(self, level_name, higher_level=None, lower_level=None):
        self.name = level_name
        self.higher_level = higher_level
        self.lower_level = lower_level
        self.read_hits = 0
        self.write_hits = 0
        self.read_misses = 0
        self.write_misses = 0
        self.evictions = 0
        self.writebacks = 0

    def access(self, operation, address):
        raise NotImplementedError

    def evict(self, block_address):
        raise NotImplementedError

    def is_dirty(self, block_address):
        raise NotImplementedError

    def invalidate(self, block_address):
        raise NotImplementedError

    def report_hit(self, operation, address):
        if operation == 'R':
            self.read_hits += 1
        else:
            self.write_hits += 1
        print(f"{self.name}: {'read' if operation == 'R' else 'write'} hit at address 0x{address:08x}")

    def report_miss(self, operation, address):
        if operation == 'R':
            self.read_misses += 1
        else:
            self.write_misses += 1
        print(f"{self.name}: {'read' if operation == 'R' else 'write'} miss at address 0x{address:08x}")

    def report_eviction(self, block_address):
        self.evictions += 1
        print(f"{self.name}: evicted cache line at 0x{block_address:08x}")

    def report_writeback(self, block_address):
        self.writebacks += 1
        print(f"{self.name}: performing writeback of cache line 0x{block_address:08x}")

    def report_statistics(self):
        print(f"{self.name} Statistics")
        print(f"\t{self.read_hits + self.write_hits} hits ({self.read_hits} read, {self.write_hits} write)")
        print(f"\t{self.read_misses + self.write_misses} misses ({self.read_misses} read, {self.write_misses} write)")
        print(f"\t{self.evictions} evictions")
        print(f"\t{self.writebacks} writebacks")

    def __repr__(self):
        return f"{self.name}"


class Memory(Level):
    """
    Defines the last layer of the memory hierarchy, the memory itself. Always hits on reads/writes
    """
    def __init__(self):
        super().__init__('Memory')

    def access(self, operation, address):
        # Assume memory always hits on reads/writes
        self.report_hit(operation, address)
        return True

    def evict(self, cache_index):
        return

    def is_dirty(self, block_address):
        return False

    def invalidate(self, block_address):
        return
