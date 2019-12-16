from setuptools import setup, find_packages

setup(
    name='bridgepy',
    version='0.1.0',
    license='proprietary',
    description='bridge player server',

    author='Powell Quiring',
    author_email='powellquiring@gmail.com',
    url='https://powellquiring.com',

    packages=find_packages(where='src'),
    package_dir={'': 'src'},

    install_requires=['click'],

    entry_points={
        'console_scripts': [
            'bridgepy = bridgepy.cli:cli',
        ]
    },
)

