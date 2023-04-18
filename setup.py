"""
Python API client for VA Notify
"""

import ast
import re
from setuptools import setup, find_packages


_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('notifications_utils/version.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

setup(
    name='notification-utils',
    version=version,
    url='https://github.com/department-of-veterans-affairs/notification-utils',
    license='MIT',
    author='Department of Veteran Affairs',
    # author_email is required if the author is specified.
    author_email='unspecified',
    description='Shared python code for VA Notify. Forked from https://github.com/cds-snc/notification-utils',
    long_description=__doc__,
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'bleach>=4.1.0',
        'boto3>=1.24.61',
        'botocore>=1.27.61',
        'Flask>=1.1.1',
        'Flask-Redis>=0.4.0',
        'Jinja2>=2.11.3',
        'mistune==0.8.4',
        'monotonic>=1.6',
        'orderedset>=2.0.3',
        'phonenumbers~=8.12.12',
        'pypdf2 ~= 3.0.1',
        'python-json-logger~=2.0.7',
        'pytz>=2021.3',
        'pyyaml==5.4.1',
        'requests>=2.26.0',
        'smartypants>=2.0.1',
        'statsd>=3.3.0',
    ]
)
