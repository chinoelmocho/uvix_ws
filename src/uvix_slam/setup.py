from setuptools import find_packages, setup
import os
from glob import glob
package_name = 'uvix_slam'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), [f for f in glob(os.path.join('launch', '*')) if os.path.isfile(f)]),
        (os.path.join('share', package_name, 'config'), [f for f in glob(os.path.join('config', '*')) if os.path.isfile(f)]),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='chino',
    maintainer_email='guncayre@gmail.com',
    description='TODO: Package description',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
        ],
    },
)
