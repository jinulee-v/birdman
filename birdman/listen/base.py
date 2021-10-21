from abc import ABCMeta, abstractmethod


class BaseListener(object):
    """BaseListener class contains:

    Methods:
        listen : listens and reacts to the dictionary it is provided.
                 Since streamers provide dict with its own unique set of keys,
                 Listeners should be aware of such different formats.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def listen(self, result):
        '''Must override.
        Listens to the result object(dict) and process it however you like.
        '''
        pass