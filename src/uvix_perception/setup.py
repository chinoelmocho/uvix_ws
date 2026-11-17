import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'uvix_perception'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='UVIX team',
    maintainer_email='guncayre@gmail.com',
    description='Synthetic visual observations for M1-03.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={'console_scripts': [
        'synthetic_perception_provider = uvix_perception.synthetic_provider:main',
    ]},
)
