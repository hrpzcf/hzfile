# coding: utf-8

from setuptools import find_packages, setup

from hzfile import AUTHOR, EMAIL, NAME, VERSION, WEBSITE

description = "一个用于学习的模块，用于自定义的'.hz'格式文件的生成和读取。"
try:
    with open("README.md", "r", encoding="utf-8") as md:
        long_description = md.read()
except Exception:
    long_description = description

setup(
    name=NAME,
    version=VERSION,
    author=AUTHOR,
    author_email=EMAIL,
    maintainer=AUTHOR,
    maintainer_email=EMAIL,
    url=WEBSITE,
    description=description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT License",
    packages=find_packages(),
    # platforms=[],
    # install_requires=[],
    python_requires=">=3.5",
    classifiers=[
        "Intended Audience :: Developers",
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    keywords=["hz", ".hz", "hz file"],
)
