from setuptools import setup


setup(
    name='django-delayed-mailer',
    version='0.1',
    description='Django delayed mailer',
    long_description=open('README.rst').read(),
    author='Andy McKay',
    author_email='andym@mozilla.com',
    license='BSD',
    packages=['delayed_mailer'],
    url='https://github.com/andymckay/django-delayed-mailer',
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Framework :: Django'
        ],
    )
