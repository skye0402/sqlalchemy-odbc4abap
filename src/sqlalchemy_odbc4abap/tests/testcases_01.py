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

connection_string = f"{DIALECT_DBAPI}://{USERNAME}:{PASSWORD}@MYDSN"
# Create the engine
engine = create_engine(url=connection_string, echo=True, echo_pool=True)

# Connect to the database
with engine.connect() as connection:
    result = connection.execute(text("SELECT * FROM SYS.VIEWS WHERE schema_name = 'SYS'"))
    for row in result:
        print(row)
    connection.detach()
connection.close()
# You can run the test cases with 

class TestProxyOpenAI(unittest.TestCase):
    
    def connect_to_database(self):
        try:
            # Connect to the database
            with engine.connect() as connection:
                result = connection.execute(text("SELECT * FROM SYS.VIEWS WHERE schema_name = 'SYS'"))
                for row in result:
                    print(row)
                connection.detach()
            connection.close()
        except Exception as e:
            print(f"Error connecting: {e}")
            self.assertTrue(False)


        test_string = "Hello I'm an AI."

        self.assertTrue(test_string in test_string)

    def test_openai_llm(self):
        try:
            from saplangchainproxy.llm import SAPAzureOpenAI
        except Exception as e:
            print(f"Error importing: {e}")
            self.assertTrue(False)
        llm = SAPAzureOpenAI(temperature=0.0)
        test_string = "Hello I'm an AI."
        test_reply = llm(f"Just answer with '{test_string}'. Nothing else.")
        self.assertTrue(test_string in test_reply)

    def test_embeddings(self):
        try:
            from saplangchainproxy.embeddings import SAPOpenAIEmbeddings
        except Exception as e:
            print(f"Error importing: {e}")
            self.assertTrue(False)
        embeddings_model = SAPOpenAIEmbeddings(model='text-embedding-ada-002-v2')
        embeddings = embeddings_model.embed_documents([
            "Hi there!",
            "Hello World!"
        ])
        len(embeddings), len(embeddings[0]) 

