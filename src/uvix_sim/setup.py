import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'Uvix_sim'

data_files = [
    ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
    ('share/' + package_name, ['package.xml']),
    (os.path.join('share', package_name, 'worlds'), [f for f in glob(os.path.join('worlds', '*')) if os.path.isfile(f)]),
    (os.path.join('share', package_name, 'meshes'), [f for f in glob(os.path.join('meshes', '*')) if os.path.isfile(f)]),
    (os.path.join('share', package_name, 'urdf'), [f for f in glob(os.path.join('urdf', '*')) if os.path.isfile(f)]),
    (os.path.join('share', package_name, 'launch'), [f for f in glob(os.path.join('launch', '*')) if os.path.isfile(f)]),
    (os.path.join('share', package_name, 'config'), [f for f in glob(os.path.join('config', '*')) if os.path.isfile(f)]),
    (os.path.join('share', package_name, 'maps'), [f for f in glob(os.path.join('maps', '*')) if os.path.isfile(f)]),
]

for path, dirs, files in os.walk('models'):
    install_dir = os.path.join('share', package_name, path)
    data_files.append((install_dir, [os.path.join(path, f) for f in files if not f.startswith('.')]))

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=data_files,
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='chino',
    maintainer_email='chino@todo.todo',
    description='TODO: Package description',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'gazebo_ready_watcher = Uvix_sim.gazebo_ready_watcher:main',
            'slam_prereq_checker = Uvix_sim.slam_prereq_checker:main',
            'patrol_node = Uvix_sim.patrol_node:main',
            'range_fix = Uvix_sim.range_fix:main',
            'slam_points_node = Uvix_sim.slam_points_node:main',
        ],
    },
)
