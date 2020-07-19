from setuptools import setup, find_packages

with open('README.md', 'r') as fh:
    long_description = fh.read()

setup(
    name='Flask-Consent',
    url='https://github.com/02JanDal/Flask-Consent',
    license='MIT',
    author='Jan Dalheimer',
    author_email='jan@dalheimer.de',
    description='Handle user (cookie) consent in Flask projects',
    long_description=long_description,
    long_description_content_type='text/markdown',
    zip_safe=True,
    packages=find_packages(),
    install_requires=[
        'Flask>=1.0.0'
    ],
    package_data=dict(flask_consent=['injection.html']),
    setup_requires=['pytest-runner'],
    test_suite='tests',
    tests_require=[
        'pytest',
        'Flask-Testing'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Flask',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Internet :: WWW/HTTP'
    ],
    python_requires='~=3.7'
)
