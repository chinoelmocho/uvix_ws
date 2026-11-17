from setuptools import setup

setup(name='uvix_audio', version='0.1.0', packages=['uvix_audio'],
      data_files=[
          ('share/ament_index/resource_index/packages', ['resource/uvix_audio']),
          ('share/uvix_audio', ['package.xml']),
          ('share/uvix_audio/launch', ['launch/fake_voice.launch.py']),
      ],
      description='Synthetic voice fixtures for M1-04 contract validation',
      install_requires=['setuptools'], zip_safe=True, tests_require=['pytest'],
      entry_points={'console_scripts': [
          'fake_voice_provider = uvix_audio.fake_voice_node:main',
      ]})
