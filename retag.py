import os
import itertools
from sync import fix_tags

def main():
    """

    """
    for path, dirs, files in itertools.chain(os.walk('/media/COWON J3/Music/'),
                                             os.walk('/media/MicroSD/Music/')):
        dirs.sort()
        files.sort()
        fix_tags([os.path.join(path, file) for file in files])

if __name__ == '__main__':
    main()