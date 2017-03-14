import os
import sys
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

VERSION = CHANGES.splitlines()[0]

install_requires = [
    'pyramid',
    'jsonschema',
    'ramlfications>=0.1.9',
]

tests_require = install_requires + [
    'pytest',
    'pytest-cov',
    'WebTest',
    'six',
    'inflection'
]
testing_extras = tests_require + [
    'nose',
    'coverage',
]

setup(name='pyramlson',
    version=VERSION,
    description='pyramlson',
    long_description=README + '\n\n' + CHANGES,
    classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
    author='ScanPlus GmbH',
    author_email='devops@scanplus.de',
    url='https://github.com/ScanPlusGmbH/pyramlson',
    keywords='web pyramid api json',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require = {
        'testing': testing_extras,
    },
    test_suite="pyramlson",
)
