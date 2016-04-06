from setuptools import setup, find_packages
setup(
    name = "chewfit",
    version = "0.0.3",
    packages = find_packages(),
    install_requires=[
        'httplib2>=0.9.1',
        'google-api-python-client',
        'six',
    ],
    entry_points={
        'console_scripts': [
            'chewfit=chewfit.cli:run',
        ],
    } 
)
