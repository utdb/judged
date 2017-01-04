from judged import CacheError


class NoCache:
    """
    Sentinel cache used to raise error when cache is hit without configuring caching.
    """
    def clear(self):
        """Clear gets a pass because it can legitimately be invoked without relation to caching."""
        pass

    def fail(*args, **kwargs):
        """Raises cache error to notify user of configuration problem."""
        raise CacheError("Native predicate tried to use cache without configured caching mechanism.")

    get = __getitem__ = __setitem__ = __delitem__ = fail


DictCache = dict


class ReportingCache:
    def __init__(self):
        self.cache = dict()

    def clear(self):
        self.cache.clear()

    def get(self, key, default=None):
        sentinel = object()
        result = self.cache.get(key, sentinel)
        if result is sentinel:
            print("CACHE MISS")
            return default
        else:
            print("CACHE HIT")
            return result

    def __getitem__(self, key):
        return self.cache[key]

    def __setitem__(self, key, value):
        print("CACHE STORE {} -> ".format(key))
        for e in value:
            print("                  {}".format(e))
        result = self.cache[key] = value
        return result

    def __delitem__(self, key):
        del self.cache[key]
