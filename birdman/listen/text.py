from birdman.listen.base import BaseListener


class format_dict(dict):
    """Helper class for easy formatting.
    """

    def __missing__(self, key):
        return ""


class TextListener(BaseListener):
    """TextListener records the result dict in given format to the desired file.
    formatstr decides your desired text format.
    It is directly fed to built-in format() function, so check "python format() named placeholder syntax" for good.
    """

    def __init__(self, file, encoding='UTF-8', buffering=1, formatstr="{url}\t{title}\t{nickname}\t{written_at}"):
        """
        Args:
            file, encoding, bufsize: Equal to python built-in `open()`
            keys: Iterable(str).
                  If not None, only keys from this variable will be stored.
        """
        self.file = open(file, mode='a', encoding=encoding, buffering=buffering)

        self.formatstr = formatstr

    def listen(self, result):
        result = format_dict(result)
        result_str = self.formatstr.format(**result)
        self.file.write(
            result_str + '\n'
        )
