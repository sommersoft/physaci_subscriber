from setuptools import find_packages, setup

setup(
    name='physaci_subscriber',
    version='0.0.1',
    packages=find_packages(),
    package_dir={'':'src'},
    package_data={
        '': ['*.conf'],
    },
    zip_safe=False,
    install_requires=[
        'requests',
    ],
    entry_points={
        'console_scripts': [
            'physaci_send_subscription = physaci_subscriber.subscribe:subscribe_to_registrar'
        ]
    },
)
