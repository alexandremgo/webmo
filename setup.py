from setuptools import setup, find_packages

setup(
    name='WebMo',
    author='Alexandre Magaud',
    author_email='alexandre.magaud@gmail.com',
    version='0.1.0',
    install_requires=[
        "requests",
        "peewee",
        "urwid",
    ],
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'webmo = monitor.monitor:main',
        ]
    })
