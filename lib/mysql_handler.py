import logging
import math
import time

import bcrypt
import mysql.connector
import mysql.connector.pooling as pooling

module_logger = logging.getLogger('icad_tone_detection.mysql')


class DatabaseFactory:
    def __init__(self, config_data):
        self.config = config_data.get("mysql")

    def get_database(self):
        db_instance = MySQLDatabase(self.config)
        init_result = db_instance.initialize_db()

        if not init_result:
            module_logger.error("Database Initialization Failed.")
            return False

        return db_instance


class MySQLDatabase:
    """
    Represents a MySQL database with connection pooling.

    Attributes:
        dbconfig (dict): Configuration data for the MySQL connection.
        pool (pooling.MySQLConnectionPool): The connection pool instance.
    """

    def __init__(self, config_data: dict):
        """
        Initialize the MySQLDatabase with configuration data.

        Args:
            config_data (dict): Configuration data containing MySQL connection details.
        """
        self.dbconfig = {
            "host": config_data.get("host"),
            "user": config_data.get("user"),
            "password": config_data.get("password"),
            "database": config_data.get("database"),
            "port": config_data.get("port")
        }

        self._connections_in_use = 0
        self._pool_size = 25

        self.pool = pooling.MySQLConnectionPool(pool_name="icad_tone_detect", pool_size=self._pool_size,
                                                **self.dbconfig)

    def initialize_db(self):

        query = "SELECT * FROM users WHERE user_username = %s"
        params = ("admin",)
        try:
            admin_user = self.execute_query(query, params, fetch_mode="one")
        except mysql.connector.Error as e:
            module_logger.error(f"Failed to query database: {e}")
            return False

        if not admin_user['result']:
            try:
                password_hash = bcrypt.hashpw("admin".encode(), bcrypt.gensalt())
                query = "INSERT INTO users (user_username, user_password) VALUES (%s, %s)"
                params = ('admin', password_hash)
                self.execute_commit(query, params)

                query = "SELECT user_id FROM users WHERE user_username = %s"
                admin_user_id = self.execute_query(query, params=("admin",), fetch_mode="one")['result']['user_id']

                query = (
                    "INSERT INTO user_security (user_id, is_active, last_login_date, failed_login_attempts, account_locked_until) VALUES (%s, 1, %s, 0, 0)")
                params = (admin_user_id, time.time())
                self.execute_commit(query, params)
                module_logger.info("Admin user created successfully.")
                return True
            except mysql.connector.Error as e:
                module_logger.error(f"Failed to create admin user: {e}")
                return False
        else:
            module_logger.info("Admin user already exists.")
            return True

    def _acquire_connection(self):
        self._connections_in_use += 1
        return self.pool.get_connection()

    def _release_connection(self, conn):
        conn.close()
        self._connections_in_use -= 1

    def get_connections_in_use(self):
        return self._connections_in_use

    def pool_status(self) -> dict:
        """
        Retrieve the status of the connection pool.

        Returns:
            dict: A dictionary containing details about the connection pool.
        """
        return {
            'pool_name': self._pool_name,
            'pool_size': self._pool_size,
            'connections_in_use': self._connections_in_use,
            'connections_free': self._pool_size - self._connections_in_use
        }

    def get_version(self) -> str:
        """
        Get the version of the MySQL server.

        Returns:
            str: Version of the MySQL server.
        """
        result = self.execute_query("SELECT VERSION()", fetch_mode="one")
        return result['message']['VERSION()'] if result['success'] else ""

    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.

        Args:
            table_name (str): The name of the table.

        Returns:
            bool: True if the table exists, False otherwise.
        """
        query = "SHOW TABLES LIKE %s"
        result = self.execute_query(query, params=(table_name,), fetch_mode="one")
        return bool(result['message'])

    def is_connected(self) -> bool:
        """
        Check if the database is reachable.

        Returns:
            bool: True if the database is reachable, False otherwise.
        """
        try:
            with self.pool.get_connection() as conn:
                return conn.is_connected()
        except mysql.connector.Error as error:
            module_logger.error(f"<<MySQL>> Connection Check Failed: {error}")
            return False

    def execute_query(self, query: str, params=None, fetch_mode="all", fetch_count=None):
        """
        Execute a SELECT query and fetch results.

        Args:
            query (str): The SQL query string.
            params (tuple or dict, optional): The parameters for the SQL query.
            fetch_mode (str, optional): The mode to fetch results ("all", "many", or "one"). Default is "all".
            fetch_count (int, optional): The number of rows to fetch if fetch_mode is "many".

        Returns:
            dict: A dictionary containing 'success' (bool) and 'message' (str or list of results).
        """
        conn = self._acquire_connection()
        try:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(query, params)

                if fetch_mode == "all":
                    result = cursor.fetchall()
                elif fetch_mode == "many":
                    result = cursor.fetchmany(fetch_count) if fetch_count else []
                elif fetch_mode == "one":
                    result = cursor.fetchone()
                else:
                    raise ValueError(f"Invalid fetch_mode: {fetch_mode}")

                if not result:
                    result = []

                module_logger.debug(
                    f"<<MySQL>> <<Query>> Executed Successfully\n{query}\nParams: {params}\nFetch Mode: {fetch_mode}")
                return {'success': True, 'message': "MySQL Query Executed Successfully", "result": result}

        except (mysql.connector.Error, ValueError) as error:
            module_logger.error(f"<<MySQL>> <<Query>> Execution Error: {error}")
            return {'success': False, 'message': str(error), 'result': []}
        finally:
            self._release_connection(conn)

    def execute_commit(self, query: str, params=None, return_row=False, return_count=False):
        """
        Execute an INSERT, UPDATE, or DELETE query.

        Args:
            query (str): The SQL query string.
            params (tuple or dict, optional): The parameters for the SQL query.
            return_row (bool, optional): If True, return the last row ID.
            return_count (bool, optional): If True, return the number of rows affected.

        Returns:
            dict: A dictionary containing 'success' (bool), 'message' (str), and 'result' (int or empty list).
        """
        conn = self._acquire_connection()
        try:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(query, params)
                conn.commit()

                module_logger.debug(f"<<MySQL>> <<Commit>> Executed Query: {query} | Params: {params}")

                if return_row:
                    result = cursor.lastrowid
                elif return_count:
                    result = cursor.rowcount
                else:
                    result = []

                return {'success': True, 'message': 'MySQL Commit Query Executed Successfully', 'result': result}
        except mysql.connector.Error as error:
            module_logger.error(f"<<MySQL>> <<Commit>> Execution Error: {error}")
            module_logger.error(f"<<MySQL>> <<Commit>> Error: {query} {params}")
            conn.rollback()
            return {'success': False, 'message': f'MySQL Commit Query Execution Error: {error}', 'result': []}
        finally:
            self._release_connection(conn)

    def execute_many_commit(self, query: str, data: list, batch_size: int = 1000):
        """
        Execute an INSERT, UPDATE, or DELETE query for multiple data rows in batches.

        Args:
            query (str): The SQL query string.
            data (list): A list of parameter tuples for the SQL query.
            batch_size (int): The number of rows to commit in each batch.

        Returns:
            dict: A dictionary containing 'success' (bool) and 'message' (str or exception message).
        """
        if not data:
            return {'success': False, 'message': 'No data provided for batch execution.', 'result': []}

        conn = self._acquire_connection()
        try:
            total_batches = math.ceil(len(data) / batch_size)

            with conn.cursor(dictionary=True) as cursor:
                for batch_num, i in enumerate(range(0, len(data), batch_size), start=1):
                    batch_data = data[i:i + batch_size]
                    cursor.executemany(query, batch_data)
                    conn.commit()
                    module_logger.info(f"<<MySQL>> Batch {batch_num} of {total_batches} Committed Successfully")

            module_logger.debug("<<MySQL>> <<Multi-Commit>> Executed Successfully")
            return {'success': True, 'message': 'MySQL Multi-Commit Executed Successfully', 'result': []}
        except mysql.connector.Error as error:
            module_logger.error(f"<<MySQL>> <<Multi-Commit>> Error: {error} {query} {batch_data}")
            return {'success': False, 'message': f'MySQL Multi-Commit Error: {error}', 'result': []}
        finally:
            self._release_connection(conn)
