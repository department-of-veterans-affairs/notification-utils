"""
Python API client for VA Notify
"""
import re
import ast
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
    description='Shared python code for VA Notify. Forked from https://github.com/cds-snc/notification-utils',
    long_description=__doc__,
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'bleach==3.3.0',
        'mistune==0.8.4',
        'requests~=2.25',
        'idna<3',
        'python-json-logger==0.1.11',
        'Flask>=1.1.1',
        'orderedset==2.0.3',
        'Jinja2==2.11.3',
        'statsd==3.3.0',
        'Flask-Redis==0.4.0',
        'pyyaml>=5.4,<5.5',
        'phonenumbers==8.12.12',
        'pytz==2020.5',
        'smartypants==2.0.1',
        'monotonic==1.5',
        'pypdf2==1.26.0',

        # required by both api and admin
        'awscli==1.19.65',
        'boto3==1.17.65',
    ]
)
