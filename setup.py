from setuptools import setup, find_packages

# Open the requirements
with open('requirements.txt') as fp:
    req_list = fp.read().strip().split("\n")

setup(
    name='modron',
    version='0.0.1',
    packages=find_packages(),
    description='Bot to help manage play-by-post campaigns hosted on Slack',
    entry_points={
        'console_scripts': 'modron=modron.app:main'
    },
    install_requires=req_list
)
