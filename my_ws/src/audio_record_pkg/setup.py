from setuptools import find_packages, setup

package_name = 'audio_record_pkg'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='hw',
    maintainer_email='hw@example.com',
    description='ROS 2 Python package for recording audio to output.wav at 16kHz.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'audio_record = audio_record_pkg.audio_record:main',
            'whisper_asr = audio_record_pkg.whisper_asr:main',
            'pyttx3_demo = audio_record_pkg.pyttx3_demo:main',
            'edge_tts_demo = audio_record_pkg.edge_tts_demo:main',
            'voice_chat_pipeline = audio_record_pkg.voice_chat_pipeline:main',
        ],
    },
)
