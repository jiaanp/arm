from glob import glob
import os
from setuptools import find_packages, setup

package_name = 'voice_pick_place_bridge'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*.launch.py'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='hw',
    maintainer_email='hw@example.com',
    description='Standalone voice bridge for fixed-zone pick and place commands.',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'voice_pick_place_command = voice_pick_place_bridge.voice_pick_place_command:main',
            'pick_place_session = voice_pick_place_bridge.pick_place_session:main',
        ],
    },
)
