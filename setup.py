from setuptools import setup, find_packages

setup(
    name='modron',
    version='0.0.1',
    packages=find_packages(),
    description='Bot to help manage play-by-post campaigns hosted on Slack',
    install_requires=[
        'flask>=1.1',
        'humanize',
        'slackclient',
        'slackeventsapi',
        'pydantic',
        'pyyaml'
    ]
)
