import logging

def foobar():
  logger = logging.getLogger(__name__)
  logger.info('this is foobar')

class dog(object):
  def __init__(self, logger=None):
    self.logger = logger or logging.getLogger(__name__)

  def sit(self):
    self.logger.info('I sit. good dog!')
