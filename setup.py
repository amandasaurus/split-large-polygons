from setuptools import setup

setup(
    name="split-large-polygons",
    version="1.1.0",
    author="Rory McCann",
    author_email="rory@technomancy.org",
    py_modules=['split_large_polygons'],
    platforms=['any',],
    requires=[],
    entry_points={
        'console_scripts': [
            'split-large-polygons = split_large_polygons:main',
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
    ],
)
