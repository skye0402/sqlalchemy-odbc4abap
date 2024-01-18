# ODBC for ABAP (odbc4abap)

ODBC for ABAP is a Python library that provides an Open Database Connectivity (ODBC) driver for ABAP systems. This library is designed to plug into SQLAlchemy 2.0 and allows for external SQL read access to CDS objects owned by the ABAP system.

## Why an ODBC Driver for ABAP?

Direct SQL read access to the underlying SAP HANA database of an ABAP system is not recommended due to several issues outlined in SAP Note 2511210. These include unstable names and internal structures, incorrect typecasts, and bypassed ABAP-level security concepts.

By treating the ABAP system itself as a database and accessing it directly using ODBC, these problems are mitigated. Authentication and authorization are handled using an ABAP user, and full ABAP SQL semantics apply. This approach also enables the use of application-server-level buffering, ABAP-level access control, and read access logging.

Compared to the ODATA interface, the ODBC interface provides unrestricted SQL access to all exposed ABAP CDS view entities, allowing for ad-hoc joins and data aggregation for analytical queries.

## Features

- Supports the use of a technical user in the ABAP system with privileged access (no DCLs).
- Allows only read access to the exposed ABAP CDS objects.
- Integrates with SQLAlchemy 2.0 for easy use within Python applications.

## Installation

To install `odbc4abap`, you can use `pip`:

```bash
pip install odbc4abap
```

## Configuration

Please refer to SAP Note '3076454 - ODBC driver for ABAP: Configuration' for detailed configuration instructions.

## Usage

After installing and configuring the library, you can use it within your Python application to query ABAP CDS view entities. Here is an example of how to use `odbc4abap` with SQLAlchemy:

```python
from sqlalchemy import create_engine

# Create an engine that connects to the ABAP system
engine = create_engine('odbc4abap+pyodbc://username:password@dsn')

# Query the ABAP system using SQLAlchemy ORM or Core
# ...
```

## Limitations

- Currently, only read access is supported.
- The library supports the use of a technical user with privileged access only.

## License

`odbc4abap` is released under the MIT License. See the LICENSE file for more details.

## Contributions

Contributions are welcome! Please submit pull requests or open issues on the project's GitHub repository.

## Support

For support and further assistance, please refer to the SAP community forums or open an issue on the GitHub repository.

## Disclaimer

This project is not affiliated with SAP SE or its group of companies.