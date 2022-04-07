from birdman.listen import register_listener
from birdman.listen.base import BaseListener


@register_listener('text')
class TextListener(BaseListener):
    """TextListener records the result dict in given format to the desired file.
    formatstr decides your desired text format.
    It is directly fed to built-in format() function, so check "python format() named placeholder syntax" for good.
    """

    def __init__(self, obj):
        """
        Args:
            file, encoding, bufsize: Equal to python built-in `open()`
            keys: Iterable(str).
                  If not None, only keys from this variable will be stored.
        """
        super(TextListener, self).__init__(obj)

        file = obj.get('file', 'test.log')
        encoding = obj.get('encoding', 'UTF-8')
        buffering = obj.get('buffering', 1)
        self.file = open(file, mode='a', encoding=encoding, buffering=buffering)
        self.must_have_keys = obj.get('must_have_keys', ['url', 'nickname', 'wirtten_at'])

        self.formatstr = obj.get('formatstr', "{url}\t{nickname}\t{written_at}")

    def listen(self, result):
        for key in self.must_have_keys:
            if key not in result:
                result[key] = ''
        result_str = self.formatstr.format(**result)
        self.file.write(
            result_str + '\n'
        )

    def close(self):
        self.file.close()