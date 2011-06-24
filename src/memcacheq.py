class MemcacheQueue(object):
    def __init__(self, name, memcache_client):
        self.name = name
        self.mc_client = memcache_client
        
        self.last_read = '_mcq_%s_last_read' % name                
        lr = self.mc_client.get(self.last_read)
        if not lr:
            self.mc_client.set(self.last_read, 0)

        self.last_added = '_mcq_%s_last_added' % name
        la = self.mc_client.get(self.last_added)
        if not la:
            self.mc_client.set(self.last_added, 0)
        
    def __repr__(self):
        return '<MemcacheQueue %s>' % self.name

    def add(self, msg):
        l_a = self.mc_client.incr(self.last_added)
        self.mc_client.set('_mcq_%s_%s' % (self.name, l_a), msg)
        
    def get(self):
        if len(self) <= 0:
            return None
        l_r = self.mc_client.incr(self.last_read)
        msg = self.mc_client.get('_mcq_%s_%s' % (self.name, l_r))
        self.mc_client.delete('_mcq_%s_%s' % (self.name, l_r))
        return msg
        
    def __len__(self):
        l_a = self.mc_client.get(self.last_added)
        l_r = self.mc_client.get(self.last_read)
        tmp = l_a - l_r
        if tmp < 0: tmp = 0
        return tmp