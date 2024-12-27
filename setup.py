from setuptools import setup, find_packages

def parse_requirements(filename):
    with open(filename, 'r') as file:
        return file.read().splitlines()

setup(
    name='census-dashboard',
    version='0.1.0',
    packages=find_packages(),  # This should detect 'census_dashboard'
    include_package_data=True,
    install_requires=parse_requirements('requirements.txt')
)