import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'bobert_sim'

# 1. Mantenemos tu configuración original en una variable (quitamos la línea de models)
data_files = [
    ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
    ('share/' + package_name, ['package.xml']),
    
    # Tus carpetas originales
    (os.path.join('share', package_name, 'worlds'), glob(os.path.join('worlds', '*'))),
    (os.path.join('share', package_name, 'meshes'), glob(os.path.join('meshes', '*'))),
    (os.path.join('share', package_name, 'urdf'), glob(os.path.join('urdf', '*'))),
    (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*'))),
    (os.path.join('share', package_name, 'config'), glob(os.path.join('config', '*'))),
    (os.path.join('share', package_name, 'maps'), glob(os.path.join('maps', '*'))),
]

# 2. Magia recursiva para la carpeta 'models'
# Esto buscará en TODA la carpeta models y copiará subcarpetas, meshes, materiales, etc.
# Incluirá tanto los modelos del hospital como tu carpeta 'models/bobert'
for path, dirs, files in os.walk('models'):
    install_dir = os.path.join('share', package_name, path)
    list_entry = (install_dir, [os.path.join(path, f) for f in files if not f.startswith('.')])
    data_files.append(list_entry)

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=data_files, # <-- Le pasamos la lista que armamos arriba
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='chino',
    maintainer_email='chino@todo.todo',
    description='Paquete de simulacion del rover Bobert',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'gazebo_ready_watcher = bobert_sim.GazeboReadyWatcher:main',
            'slam_prereq_checker = bobert_sim.Chek_time:main',
        ],
    },
)