import os

from setuptools import setup

setup(
    name='iou',
    version='0.1.0',
    description='Promise-like data encapsulation for asynchronous behavior',
    url='https://github.com/reinecke/IOU',
    license='MIT',
    author='Eric Reinecke',
    author_email='reinecke.eric@gmail.com',
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
    ],
    install_requires=['requests'],
    packages=['iou'],
)
