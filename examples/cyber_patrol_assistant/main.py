from birdman import init_birdman_from_yaml

from birdman.listen import register_listener
from birdman.listen.text import TextListener


@register_listener('title_body')
class TitleBodyListener(TextListener):
    """TitleBodyListener records the result dict in given format to the desired file.
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
        super(TitleBodyListener, self).__init__(obj)
        self.must_have_keys = ['title', 'body']
        self.formatstr = obj.get('formatstr', "{title}▁{body}")
        
    def listen(self, result):
        result['body'] = result['body'].replace('\n', ' ')
        super(TitleBodyListener, self).listen(result)

def main():
    riggan = init_birdman_from_yaml('examples/cyber_patrol_assistant/config.yaml', 'auth.yaml')
    riggan.start()


if __name__ == "__main__":
    main()