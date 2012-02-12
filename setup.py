try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'description': 'Event warning system and traffic estimator for downtown Tulsa, Oklahoma',
    'author': 'George Louthan',
    'url': 'http://georgerloutha.nthefourth.com/projects/tulsa-event-warning',
    'download_url': 'https://bitbucket.org/duplico/event-traffic-warning/get/tip.tar.gz',
    'author_email': 'georgerlouth@nthefourth.com',
    'version': '0.1',
    'install_requires': ['nose'],
    'packages': ['NAME'],
    'scripts': [],
    'name': 'eventwarning'
}

setup(**config)