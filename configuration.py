#!/usr/bin/env ipython

# coding: utf-8

# In[4]:

import ConfigParser
import os
import logging


# In[5]:

# borrowed from: https://www.blog.pythonlibrary.org/2013/10/25/python-101-an-intro-to-configparser/
def create_config(path, configuration):
    '''
    create a configuration file at <path>
    configuration in the format {'SectionName': {'key1':'value', 'key2':'value'}, 'OtherSection' {'opt1':'value', 'opt2':'Value'}}
    
    Note: SafeConfigParser treats everything as a string 
    '''
    logger = logging.getLogger(__name__)
    config = ConfigParser.SafeConfigParser()
    for section, options in configuration.items():
        config.add_section(section)
        for key, value in options.items():
            config.set(section, key, str(value))

    try:
        with open(path, 'wb') as config_file:
            config.write(config_file)
    except Exception as e:
        logging.error(e)

def get_config(path):
    '''
    fetch configuration as a config object
    '''
    logger = logging.getLogger(__name__)
    if not os.path.exists(path):
        logging.info('creating configuration path: {path}')
        create_config(path)
    
    config = ConfigParser.SafeConfigParser()
    config.read(path)
    return config



def get_setting(path, section, setting):
    '''
    get the requested setting
    '''
    config = get_config(path)
    value = config.get(section, setting)
    return value

def update_setting(path, section, setting, value):
    '''
    update an option
    '''
    logger = logging.getLogger(__name__)
    config = get_config(config)
    config.set(section, setting, value)
    try:
        with open(path, 'wb') as config_file:
            config.write(config_file)
    except Exception as e:
        logging.error(e)
    

