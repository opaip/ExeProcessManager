from setuptools import setup, find_packages

setup(
    name="exe-process-manager",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "psutil",  # Add other dependencies here
    ],
    entry_points={
        'console_scripts': [
            'exe-process-manager = exe_process_manager:main',  # Optional if you want a command-line entry point
        ],
    },
    author="ali",
    author_email="opaipp.mi@gmail.com",
    description="A process manager for executing and monitoring .exe files.",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/opaip/ExeProcessManager",  # Replace with your actual URL
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
