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
        'bleach>=6.2.0',
        'boto3>=1.36.5',
        'botocore>=1.36.5',
        'Flask>=3.1.0',
        'Flask-Redis>=0.4.0',
        'Jinja2>=3.1.5',
        'MarkupSafe>=3.0.2',
        'mistune==3.0.2',  # Pinned: Will be addressed in #192
        'monotonic>=1.6',
        'phonenumbers~=8.13.54',
        'pypdf>= 5.1.0',
        'python-json-logger>=3.2.1',
        'pytz>=2024.2',
        'pyyaml==6.0.2',
        'requests>=2.32.3',
        'smartypants>=2.0.1',
        'statsd>=4.0.1'
    ]
)
