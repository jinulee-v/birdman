# -*- coding: utf-8 -*-

import io
import os
import sys
from setuptools import find_packages, setup


def get_version():
    about = {}
    root = os.path.abspath(os.path.dirname(__file__))
    with io.open(os.path.join(root, 'koshort', 'about.py'), encoding='utf-8') as f:
        exec(f.read(), about)

    return about


def requirements():
    def _openreq(reqfile):
        with open(os.path.join(os.path.dirname(__file__), reqfile)) as f:
            return f.read().splitlines()

    if sys.version_info >= (3, ):
        return _openreq('requirements.txt')
    else:
        raise Exception(
            "Koshort does not support python2.* distribution. consider using python3 which supports richer text formatting capability and code productivity.")


def setup_package():
    about = get_version()
    setup(
        name='birdman',
        version=about['__version__'],
        description='Birdman is a powerful package for asynchronous multi-thread streaming of any web content. Ignorantly watch over like a bird, and we will bring you the whole world. That is the virtue of unexpected ignorance.',
        long_description="""\
    (Inspired by Koshort)
    Birdman is a powerful and well-structured package for asynchronous streaming.
    Asynchronous and 
    Birdman integrates different crawlers (for differnet websites!) and streaming APIs into any listener that user require. You can create and add your own listner without any knowledge about asynchronous coding!
    Simply say out the script, and soon you will glide over the world like a bird.
            """,
        url='http://birdman.readthedocs.io',
        author='jinulee-v',
        author_email='jinulee.v@gmail.com',
        keywords=['crawling', 'streaming', 'scraping', 'text analytics'],
        classifiers=[
            'Intended Audience :: Developers',
            'Intended Audience :: Education',
            'Intended Audience :: Information Technology',
            'Intended Audience :: Science/Research',
            'Programming Language :: Python :: 3.7',
            'Topic :: Scientific/Engineering',
            'Topic :: Scientific/Engineering :: Artificial Intelligence',
            'Topic :: Scientific/Engineering :: Human Machine Interfaces',
            'Topic :: Scientific/Engineering :: Information Analysis',
            'Topic :: Text Processing',
            'Topic :: Text Processing :: Filters',
            'Topic :: Text Processing :: General',
            'Topic :: Text Processing :: Indexing',
            'Topic :: Text Processing :: Linguistic',
            'Development Status :: 2 - Pre-Alpha',
            'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        ],
        entry_points={
        },
        license='GPL v3+',
        packages=find_packages(),
        install_requires=requirements())


if __name__ == "__main__":
    setup_package()