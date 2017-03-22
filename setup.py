from distutils.core import setup

CLASSIFIERS = (
    #('Development Status :: 5 - Production/Stable'),
    ('Environment :: Console'),
    ('Environment :: Web Environment'),
    ('Intended Audience :: Developers'),
    ('Intended Audience :: Science/Research'),
    ('Intended Audience :: System Administrators'),
    ('License :: OSI Approved :: MIT License (LGPL)'),
    ('Natural Language :: English'),
    ('Operating System :: OS Independent'),
    ('Programming Language :: Python'),
    ('Programming Language :: Python :: 2'),
    ('Programming Language :: Python :: 2.3'),
    ('Programming Language :: Python :: 2.4'),
    ('Programming Language :: Python :: 2.5'),
    ('Programming Language :: Python :: 2.6'),
    ('Programming Language :: Python :: 2.7'),
    #('Programming Language :: Python :: 3'),
    #('Programming Language :: Python :: 3.0'),
    #('Programming Language :: Python :: 3.1'),
    ('Topic :: Internet :: WWW/HTTP'),
    ('Topic :: Internet :: WWW/HTTP :: Dynamic Content'),
    ('Topic :: Internet :: WWW/HTTP :: Dynamic Content :: CGI Tools/Libraries'),
    ('Topic :: Scientific/Engineering :: Visualization'),
    ('Topic :: Software Development :: Libraries :: Python Modules'),
    ('Topic :: Utilities'),
)

setup(
    name='python-earth',
    version='0.1',
    description='Python Bindings for The Earth',
    long_description="""Control your planet w/ the power of PY""",
    author="Sean Stoops & Justin Quick",
    author_email='sean.stoops@gmail.com, justquick@gmail.com',
    url='http://www.launchpad.net/~python-earth',
    #download_url='',
    platforms = ["Windows", "Linux", "Solaris", "Mac OS-X", "Unix"],
    classifiers=CLASSIFIERS,
    packages=['earth', 'earth.weather', 'earth.air', 'earth.core'],
)

