import yaml
import os

class YamlReader(object):
    def __init__(self, path):
        self.f = open(os.path.join(path, 'Procfile'), 'r')
        self.dataMap = yaml.load(self.f)
        self.f.close()
        
    def get_processes(self):
        return self.dataMap