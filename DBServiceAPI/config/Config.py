import configparser
#import os

class ConfigClass:
    def __init__(self,Configfile_Path):  
        self.Path = Configfile_Path       

    def get_config(self):
        config = configparser.ConfigParser()
        config.read(self.Path)
        return config
    
    def get_path(self):        
        p = self.Path
        return p

    def get_value(self, section, key):
        config = self.get_config()
        if config.has_option(section, key):
          return config.get(section, key)
        else: None

    def set_config(self, configuration):
        config = configparser.ConfigParser()

        for Key in configuration.keys():
            config[Key] = configuration[Key]

        with open(self.Path, 'w') as Configfile:
            config.write(Configfile)

        return True
