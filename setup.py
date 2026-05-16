"""Setup configuration for photogram package."""

from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='photogram',
    version='0.1.0',
    description='Automated 3D reconstruction from image sequences using photogrammetry',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Luke Puplett',
    author_email='lukepuplettak@gmail.com',
    url='https://github.com/yourusername/photogram',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    python_requires='>=3.8',
    install_requires=[
        'open3d>=0.17.0',
        'opencv-python>=4.8.0',
        'numpy>=1.24.0',
        'click>=8.1.0',
        'pillow>=10.0.0',
    ],
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'photogram=photogram.cli:cli',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Scientific/Engineering :: Image Processing',
    ],
)
