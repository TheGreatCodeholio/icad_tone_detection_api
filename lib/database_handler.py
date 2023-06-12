import logging
import os
import mysql
import mysql.connector.pooling as pooling
import sqlite3
from sqlite3 import Connection
from contextlib import contextmanager
from werkzeug.security import generate_password_hash

module_logger = logging.getLogger('tr_tone_detection.sqlite')


class SQLiteDatabase:
    def __init__(self, db_path):
        self.db_path = db_path
        self.schema_path = "etc/tr_tone_detect.sql"
        if not os.path.exists(self.db_path):
            self._create_database()
            self.create_admin_user()

    def _create_database(self):
        with open(self.schema_path, 'r') as f:
            schema = f.read()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript(schema)
            cursor.close()

    def create_admin_user(self):
        password = generate_password_hash("trunkdetect")
        query = "INSERT INTO users (username, password) VALUES (?, ?)"
        params = ("admin", password)
        self.execute_commit(query, params)

    @contextmanager
    def _get_connection(self) -> Connection:
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def execute_query(self, query, params=None, fetch_mode="all"):
        if "%s" in query:
            query = query.replace("%s", "?")
        with self._get_connection() as conn:
            cursor = conn.cursor()

            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                # Retrieve the column names
                column_names = [desc[0] for desc in cursor.description]

                if fetch_mode == "all":
                    rows = cursor.fetchall()
                elif fetch_mode == "many":
                    rows = cursor.fetchmany()
                elif fetch_mode == "one":
                    rows = cursor.fetchone()
                else:
                    raise ValueError(f"Invalid fetch_mode: {fetch_mode}")

                # Iterate over the rows and add them to the dictionary
                if fetch_mode == "one":
                    result = {}
                    # Iterate over the columns and add them to the dictionary
                    if rows:
                        for i, value in enumerate(rows):
                            column_name = column_names[i]
                            result[column_name] = value

                else:
                    # Create an empty dictionary to store the data
                    result = []
                    for row in rows:
                        # Create a dictionary to store the row data
                        row_dict = {}
                        # Iterate over the columns and add them to the dictionary
                        for i, value in enumerate(row):
                            column_name = column_names[i]
                            row_dict[column_name] = value
                        # Add the row dictionary to the list
                        result.append(row_dict)

            except sqlite3.Error as e:
                module_logger.error(f"SQLite Search Query <<failed:>> {e}")
                result = {}
            finally:
                cursor.close()

        return result

    def execute_commit(self, query, params=None):
        if "%s" in query:
            query = query.replace("%s", "?")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                inserted_id = cursor.lastrowid
                conn.commit()
                return True
            except sqlite3.Error as e:
                module_logger.error(f"SQLite Commit Query <<failed:>> {e}")
                conn.rollback()
                return False
            finally:
                cursor.close()

    def execute_many_commit(self, query, data):
        if "%s" in query:
            query = query.replace("%s", "?")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                if data:
                    cursor.executemany(query, data)
                else:
                    raise sqlite3.Error
                conn.commit()
                module_logger.debug(f"SQLite Commit Query <<successful>>")
                return True
            except sqlite3.Error as e:
                module_logger.error(f"SQLite Commit Query <<failed:>> {e}")
                conn.rollback()
                return False
            finally:
                cursor.close()

    def create_schema(self, schema_file):
        if os.path.isfile(self.db_path):
            print(f"Database '{self.db_path}' already exists. Skipping schema creation.")
            return

        with open(schema_file, "r") as f:
            schema = f.read()

        self.execute_commit(schema)

        print(f"Database '{self.db_path}' created from schema file '{schema_file}'.")


class MySQLDatabase:
    def __init__(self, config_data):
        self.dbconfig = {
            "host": config_data["mysql"]["host"],
            "user": config_data["mysql"]["user"],
            "password": config_data["mysql"]["password"],
            "database": config_data["mysql"]["database"],
            "port": config_data["mysql"]["port"]
        }
        self.pool = pooling.MySQLConnectionPool(pool_name="escanner", pool_size=config_data["mysql"]["pool_size"],
                                                **self.dbconfig)

    def execute_query(self, query, params=None, fetch_mode="all"):
        conn = self.pool.get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if fetch_mode == "all":
                result = cursor.fetchall()
            elif fetch_mode == "many":
                result = cursor.fetchmany()
            elif fetch_mode == "one":
                result = cursor.fetchone()
            else:
                raise ValueError(f"Invalid fetch_mode: {fetch_mode}")

        except mysql.connector.errors.PoolError as error:
            module_logger.error(f"MySQL Search Query <<failed:>> {error}")
            result = []
        finally:
            cursor.close()
            conn.close()

        module_logger.debug(f"MySQL Search Query <<success:>>")
        return result

    def execute_commit(self, query, params=None, return_row=None):
        conn = self.pool.get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            module_logger.debug(f"MySQL Commit Query <<success:>>")
            if return_row is not None:
                return cursor.lastrowid
            else:
                return True
        except mysql.connector.errors.PoolError as error:
            module_logger.error(f"MySQL Commit Query <<failed:>> {error}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()

    def execute_many_commit(self, query, data):
        conn = self.pool.get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            if data:
                cursor.executemany(query, data)
            else:
                raise mysql.connector.errors.PoolError
            conn.commit()
            module_logger.debug(f"MySQL Commit Query <<success:>>")
            return True
        except mysql.connector.errors.PoolError as error:
            module_logger.error(f"MySQL Commit Query <<failed:>> {error}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
