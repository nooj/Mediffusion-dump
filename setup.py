import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


setuptools.setup(
    name="mediffusion",
    version="0.6.0",
    author="Bardia Khosravi",
    author_email="bardiakhosravi95@gmail.com",
    description="Diffusion Models for Medical Imaging",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/BardiaKh/Mediffusion",
    packages = setuptools.find_packages(where="mediffusion"),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "bkh-pytorch-utils==0.8.9", #v: 0.8.3
        "torchextractor==0.3.0",
        "OmegaConf==2.0.0",
    ],
    package_data={
        'mediffusion': ['./default_config/default.yaml'],
    },
    package_dir = {"": "mediffusion"},
    python_requires='>=3.8',
)
