# Research Collaboration Network (rcn_py)

[![PyPI - Version](https://img.shields.io/pypi/v/rcn-py.svg)](https://pypi.org/project/rcn-py)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/rcn-py.svg)](https://pypi.org/project/rcn-py)

-----

This research collaboration web application leverages data from multiple research databases, including Scopus, OpenAlex, and RSD, and is built using the Neo4j database and d3 visualization technology.

**Table of Contents**

- [Installation](#installation)
- [Usage](#usage)
- [License](#license)

## Installation

To install rcn-py, you can simply use pip:
```console
pip install rcn-py
```

## Usage

The `rcn-py` package utilizes data from various research sources including OpenAlex, Scopus, and RSD. Please note the following details about data handling in our package:

- OpenAlex: Data is directly accessed through their API.

- Scopus and RSD: For optimal performance, we've pre-stored data from Scopus and RSD in a Neo4j Graph Database. Users are required to manage the data storage for these two sources on their own.

Detailed instructions for setting up and managing data can be found in the `Workflow_D3.ipynb` Jupyter notebook in the repository https://github.com/NLeSC/rcn_py. We highly recommend going through this notebook to understand the complete workflow and data requirements of the `rcn-py` package.

After the database has been properly set up and is in use, ensure that all constraints in the Neo4j database have been built. This step is critical to maintaining efficient database search operations.

Then, confirm that the database is active.

To run the application, use the following command in your terminal:

```console
python3 rcn_d3.py [uri] [username] [password]
```

Replace [uri], [username], and [password] with your Neo4j database's URI, your username, and your password, respectively.

By running this command, you'll start the rcn-py application, which will utilize the data in your Neo4j database to generate insights about co-author networks.

## License

`rcn-py` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
