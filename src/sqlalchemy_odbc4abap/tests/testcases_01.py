import unittest
import os
from sqlalchemy import create_engine, text
from sqlalchemy.dialects import registry
from dotenv import load_dotenv

load_dotenv()

USERNAME = os.getenv("USERNAME", "")
PASSWORD = os.getenv("PASSWORD", "")
DIALECT_DBAPI = "odbc4abap+pyodbc"
DRIVERPATH = os.getenv("LD_LIBRARY_PATH")
ECHO_ACTIVE = False

# Register dialect
registry.register(
    "odbc4abap.pyodbc", "sqlalchemy_odbc4abap.pyodbc", "O4ADialect_pyodbc"
)

# Define the connection string (DSN-less connection)
additional_kwargs = {
    "schema": "ZORDERS_GUNTER"
}
additional_kwargs = {
    "schema": "ZGUN01"
}

class TestODBC4ABAPDialect(unittest.TestCase):
    def setUp(self) -> None:
        connection_string = f"{DIALECT_DBAPI}://{USERNAME}:{PASSWORD}@MYDSN"
        self.engine = create_engine(url=connection_string, echo=True, echo_pool=True)
    
    def test_01_retrieve_data(self):
        result = ""
        try:
            # Connect to the database            
            with self.engine.connect() as connection:
                result = connection.execute(text("SELECT * FROM SYS.DUMMY"))
                for row in result:
                    result = row[0]
                connection.detach()
            connection.close()
        except Exception as e:
            print(f"Error connecting: {e}")
            self.assertTrue(False)
        self.assertEqual(result, "X") # Dummy table contains value X in one row.
    
    def tearDown(self) -> None:
        pass
        
if __name__ == '__main__':
    unittest.main()