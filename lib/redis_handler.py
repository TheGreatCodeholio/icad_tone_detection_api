import datetime
import json
import logging
import socket

import redis

module_logger = logging.getLogger('icad_tone_detection.redis')


class RedisCache:
    """
        Represents a Redis cache handler.

        Attributes:
            connection_pool (ConnectionPool): Pool of Redis connections.
            client (Redis): Redis client for operations.
    """

    def __init__(self, config_data):
        """
            Initialize the RedisCache with configuration data.

            Args:
                config_data (dict): Configuration data containing Redis connection details.
        """

        self.connection_pool = redis.ConnectionPool(
            host=config_data["redis"]["host"],
            port=config_data["redis"]["port"],
            db=0,
            password=config_data["redis"].get("password"),
            socket_timeout=5,
            socket_connect_timeout=5,
            socket_keepalive=True,
            socket_keepalive_options={
                socket.TCP_KEEPCNT: 4,
                socket.TCP_KEEPIDLE: 5,
                socket.TCP_KEEPINTVL: 5,
            }
        )
        self.client = redis.Redis(connection_pool=self.connection_pool)

    def stop(self):
        self.client.close()
        self.connection_pool.close()

    def is_connected(self):
        try:
            # Returns True if no exception
            return self.client.ping()
        except redis.ConnectionError:
            return False

    def pool_status(self) -> dict:
        """
        Retrieve the status of the connection pool.

        Returns:
            dict: A dictionary containing details about the connection pool.
        """
        return {
            'max_connections': self.connection_pool.max_connections,
            'created_connections': self.connection_pool._created_connections,
            'connections_in_use': len(self.connection_pool._in_use_connections),
            'connections_free': self.connection_pool.max_connections - len(self.connection_pool._in_use_connections)
        }

    def get_pipeline(self):
        """
        Get a Redis pipeline.

        Returns:
            Redis pipeline instance.
        """
        return self.client.pipeline()

    def get(self, key):
        """
        Get value from Redis using a specified key.

        Args:
            key (str): The key to fetch.

        Returns:
            dict: A dictionary containing 'success' (bool) and 'message' (str or bytes).
        """
        try:
            value = self.client.get(key)
            if not value:
                value = None
            else:
                value = self.deserialize_from_redis(value.decode("utf-8"))

            module_logger.debug(f"Redis Get Key <<success>>: {key}")
            return {'success': True, 'message': 'success', 'result': value}
        except redis.RedisError as error:
            error_msg = f"Redis Get Key <<failed>>: {key}, error: {error}"
            module_logger.error(error_msg)
            return {'success': False, 'message': error_msg}

    def set(self, key, value, ttl=None):
        """
                Set a key-value pair in Redis with optional expiration.

                Args:
                    key (str): The key to set.
                    value (str): The value for the key.
                    ttl (int, optional): Expiration time in seconds.

                Returns:
                    dict: A dictionary containing 'success' (bool) and 'message' (str).
        """
        try:
            serialized_value = self.serialize_for_redis(value)
            if ttl:
                self.client.setex(key, ttl, serialized_value)
            else:
                self.client.set(key, serialized_value)
            module_logger.debug(f"Redis Set Key <<success>>: {key}")
            return {'success': True, 'message': 'success', 'result': 0}
        except redis.RedisError as error:
            error_msg = f"Redis Set Key <<failed>>: {key}, error: {error}"
            module_logger.error(error_msg)
            return {'success': False, 'message': error_msg}

    def incrby(self, key, increment=1):
        """
        Increment (or decrement) the value of a Redis key.

        Args:
            key (str): The key whose value is to be modified.
            increment (int, optional): The amount by which to increment (or decrement if negative). Default is 1.

        Returns:
            dict: A dictionary containing 'success' (bool), 'message' (str), and 'new_value' (int).
        """
        try:
            new_value = self.client.incr(key, increment)
            module_logger.debug(f"Redis Incr <<success>>: {key} by {increment}")

            return {
                'success': True,
                'message': 'success',
                'result': new_value
            }

        except redis.RedisError as error:
            error_msg = f"Redis Incr <<failed>>: {key}, error: {error}"
            module_logger.error(error_msg)
            return {'success': False, 'message': error_msg}

    def delete(self, *keys):
        """
                Delete a key from Redis.

                Args:
                    *keys (str): The key or keys to delete.

                Returns:
                    dict: A dictionary containing 'success' (bool) and 'message' (str).
        """
        try:
            existing_keys = [key for key in keys if self.client.exists(key)]
            if not existing_keys:
                msg = "No matching keys found for deletion."
                module_logger.warning(msg)
                return {'success': False, 'message': msg, 'result': 0}

            deleted_count = self.client.delete(*existing_keys)

            module_logger.debug(f"Redis Delete Key(s) <<success>>: Deleted {deleted_count} key(s)")
            return {'success': True, 'message': 'success', 'result': deleted_count}
        except redis.RedisError as error:
            error_msg = f"Redis Delete Key(s) <<failed>>: {', '.join(keys)}, error: {error}"
            module_logger.error(error_msg)
            return {'success': False, 'message': error_msg}

    def hget(self, hash_names=None, keys=None, all=False):
        """
        Fetch the value(s) associated with key(s) from a Redis hash.

        Args:
            hash_names (list): A list of hash names to get * requires all=True
            keys (list): The key(s) in the hash.
            all (bool): If True, fetches the entire hash. Default is False. * require list of hash_names

        Returns:
            dict: A dictionary containing 'success' (bool) and 'message' (str or bytes).
        """
        try:
            if all:
                pipeline = self.client.pipeline()
                if not hash_names:
                    error_msg = f"Redis HGetAll Key(s) <<failed>>, error: requires a list of hash_names"
                    module_logger.error(error_msg)
                    return {'success': False, 'message': error_msg}

                for name in hash_names:
                    pipeline.hgetall(name)

                raw_data_list = pipeline.execute()
                processed_data_list = []

                for raw_data in raw_data_list:
                    if not raw_data:
                        processed_data_list.append(None)
                    else:
                        processed_data = {k.decode("utf-8"): self.deserialize_from_redis(v.decode("utf-8")) for k, v in
                                          raw_data.items()}
                        processed_data_list.append(processed_data)

            elif keys:
                if len(hash_names) == 1:
                    name = hash_names[0]
                    raw_values = self.client.hmget(name, *keys)
                    processed_data_list = [dict(
                        zip(keys, [self.deserialize_from_redis(v.decode("utf-8")) if v else None for v in raw_values]))]
                else:
                    msg = "Please provide only one hash name when fetching specific keys."
                    module_logger.warning(msg)
                    return {'success': False, 'message': msg}

            else:
                msg = "Please provide keys to fetch or set all=True to fetch the entire hash."
                return {'success': False, 'message': msg}

            if hash_names is not None:
                if len(hash_names) == 1:
                    processed_data_list = processed_data_list[0]

            if keys is not None:
                if len(keys) == 1:
                    processed_data_list = processed_data_list

            module_logger.debug(f"Redis HGet Key(s) <<success>>: {', '.join(hash_names)}")
            return {'success': True, 'message': 'success', 'result': processed_data_list}

        except redis.RedisError as error:
            error_msg = f"Redis HGet Key(s) <<failed>>: {'/'.join(hash_names)}, error: {error}"
            module_logger.error(error_msg)
            return {'success': False, 'message': error_msg}

    def hset(self, hash_key, key=None, value=None, mapping=None, ttl=None):
        """
        Set a key-value pair or multiple key-value pairs in a Redis hash and optionally set a TTL.

        Args:
            hash_key (str): The name of the hash.
            key (str, optional): The key in the hash. Only used if mapping is None.
            value (any, optional): The value for the key. Only used if mapping is None.
            mapping (dict, optional): A dictionary of key-value pairs.
            ttl (int, optional): The time-to-live in seconds for the hash key.

        Returns:
            dict: A dictionary containing 'success' (bool) and 'message' (str) and 'fields_added' (int).
        """
        try:
            if not mapping and (key is None or value is None):
                raise ValueError("If mapping is not provided, both key and value must be set.")

            fields_added = 0

            # Prepare individual key-value pair for Redis
            if not mapping:
                value = self.serialize_for_redis(value)
                fields_added = self.client.hset(hash_key, key, value)
                module_logger.debug(f"Redis HSet Key-Value <<success>>: {hash_key}/{key}")

            # Prepare entire mapping for Redis
            else:
                prepared_mapping = {k: self.serialize_for_redis(v) for k, v in mapping.items()}
                fields_added = self.client.hset(hash_key, mapping=prepared_mapping)
                module_logger.debug(f"Redis HSet Hash <<success>>: {hash_key} with mapping")

            # Set TTL if provided and if TTL is not already set for the hash
            if ttl:
                self.client.expire(hash_key, ttl)
                module_logger.debug(f"Redis TTL set for {hash_key}: {ttl} seconds")

            return {'success': True, 'message': 'success', 'result': fields_added}

        except (redis.RedisError, ValueError) as error:
            error_msg = f"Redis HSet <<failed>>: {hash_key}/{key if key else ''}, error: {error}"
            module_logger.error(error_msg)
            return {'success': False, 'message': error_msg}

    def hdel(self, name, *keys):
        """
        Delete one or more keys from a Redis hash.

        Args:
            name (str): The name of the hash.
            keys (str): One or more keys to delete.

        Returns:
            dict: A dictionary containing 'success' (bool), 'message' (str), and 'keys_deleted' (int).
        """
        try:
            if not self.client.exists(name):
                error_msg = f"Redis hash {name} does not exist."
                module_logger.warning(error_msg)
                return {'success': False, 'message': error_msg, 'keys_deleted': 0}

            keys_deleted = self.client.hdel(name, *keys)

            if keys_deleted:
                module_logger.debug(f"Redis HDel Keys <<success>>: {name}/{keys}")
                return {'success': True, 'message': 'success', 'result': keys_deleted}
            else:
                module_logger.warning(f"Keys not found in Redis hash {name}: {keys}")
                return {'success': False, 'message': 'Keys not found', 'result': 0}

        except redis.RedisError as error:
            error_msg = f"Redis HDel Key <<failed>>: {name}/{keys}, error: {error}"
            module_logger.error(error_msg)
            return {'success': False, 'message': error_msg}

    def hincrby(self, hash_name, key, increment=1):
        """
        Increment (or decrement) the value associated with a key in a Redis hash.

        Args:
            hash_name (str): The name of the hash.
            key (str): The key whose value is to be modified.
            increment (int, optional): The amount by which to increment (or decrement if negative). Default is 1.

        Returns:
            dict: A dictionary containing 'success' (bool), 'message' (str), and 'new_value' (int).
        """
        try:
            # If the hash doesn't exist, return an error
            if not self.client.exists(hash_name):
                error_msg = f"Redis hash {hash_name} does not exist."
                module_logger.warning(error_msg)
                return {'success': False, 'message': error_msg}

            new_value = self.client.hincrby(hash_name, key, increment)
            module_logger.debug(f"Redis HIncrBy <<success>>: {hash_name}/{key} by {increment}")

            return {
                'success': True,
                'message': 'success',
                'result': new_value
            }

        except redis.RedisError as error:
            error_msg = f"Redis HIncrBy <<failed>>: {hash_name}/{key}, error: {error}"
            module_logger.error(error_msg)
            return {'success': False, 'message': error_msg}

    def rpush(self, list_name, *values, trim_to_length=None):
        """
        Append one or multiple values to a Redis list and optionally trim the list to a specified length.

        Args:
            list_name (str): The name of the list.
            *values (any): One or more values to append to the list.
            trim_to_length (int, optional): If provided, trims the list to this length from the right.

        Returns:
            dict: A dictionary containing 'success' (bool) and 'message' (str or int).
        """
        try:
            # Serialize values before pushing
            serialized_values = [self.serialize_for_redis(value) for value in values]

            # rpush to the list
            length_of_list = self.client.rpush(list_name, *serialized_values)

            # Trim the list if trim_to_length is provided
            if trim_to_length is not None:
                # Calculate the starting index for the trim based on the desired list length
                trim_start = length_of_list - trim_to_length
                # Ensure the starting index is not negative, otherwise, trim the entire list
                trim_start = max(0, trim_start)
                self.client.ltrim(list_name, trim_start, -1)

            module_logger.debug(f"Redis RPush to List {list_name} <<success>>: Appended values: {values}")
            return {'success': True, 'message': 'success', 'result': length_of_list}
        except redis.RedisError as error:
            error_msg = f"Redis RPush to List {list_name} <<failed>>, error: {error}"
            module_logger.error(error_msg)
            return {'success': False, 'message': error_msg}

    def lpush(self, list_name, *values, trim_to_length=None):
        """
        Prepend one or multiple values to a Redis list and optionally trim the list to a specified length.

        Args:
            list_name (str): The name of the list.
            *values (any): One or more values to prepend to the list.
            trim_to_length (int, optional): If provided, trims the list to this length from the left.

        Returns:
            dict: A dictionary containing 'success' (bool) and 'message' (str or int).
        """
        try:
            # Serialize values before pushing
            serialized_values = [self.serialize_for_redis(value) for value in values]

            # lpush to the list
            length_of_list = self.client.lpush(list_name, *serialized_values)

            # Trim the list if trim_to_length is provided
            if trim_to_length is not None:
                self.client.ltrim(list_name, 0, trim_to_length - 1)

            module_logger.debug(f"Redis LPush to List {list_name} <<success>>: Prepended values: {values}")
            return {'success': True, 'message': 'success', 'result': length_of_list}
        except redis.RedisError as error:
            error_msg = f"Redis LPush to List {list_name} <<failed>>, error: {error}"
            module_logger.error(error_msg)
            return {'success': False, 'message': error_msg}

    def lpop(self, list_name):
        """
        Remove and return the first value of a Redis list.

        Args:
            list_name (str): The name of the list.

        Returns:
            dict: A dictionary containing 'success' (bool) and 'message' (str or any).
        """
        try:
            raw_value = self.client.lpop(list_name)
            deserialized_value = None

            if raw_value:
                if isinstance(raw_value, bytes):
                    deserialized_value = self.deserialize_from_redis(raw_value.decode("utf-8"))
                else:
                    deserialized_value = self.deserialize_from_redis(raw_value)

            module_logger.debug(f"Redis LPop from List {list_name} <<success>>: Popped value: {deserialized_value}")

            return {
                'success': True,
                'message': f'Value popped from list {list_name}',
                'result': deserialized_value
            }
        except redis.RedisError as error:
            error_msg = f"Redis LPop from List {list_name} <<failed>>, error: {error}"
            module_logger.error(error_msg)
            return {'success': False, 'message': error_msg}

    def lrange(self, list_name, start=0, end=-1):
        """
        Retrieve a subrange of values from a Redis list between the specified indices.

        Args:
            list_name (str): The name of the list.
            start (int): The starting index of the range. Defaults to 0 (first element).
            end (int): The ending index of the range. Defaults to -1 (last element).

        Returns:
            dict: A dictionary containing 'success' (bool), 'message' (str), and optionally 'result' (list of deserialized values).
        """
        try:
            # Use the lrange Redis command to get the values
            values = self.client.lrange(list_name, start, end)

            # Deserialize the values before returning them
            deserialized_values = [self.deserialize_from_redis(value) for value in values]

            module_logger.debug(
                f"Redis LRange on List {list_name} <<success>>: Retrieved values: {deserialized_values}")
            return {'success': True, 'message': 'success', 'result': deserialized_values}
        except redis.RedisError as error:
            error_msg = f"Redis LRange on List {list_name} <<failed>>, error: {error}"
            module_logger.error(error_msg)
            return {'success': False, 'message': error_msg}

    def zadd(self, set_name, member_score_mapping):
        """
        Add members with their respective scores to a Redis sorted set.

        Args:
            set_name (str): The name of the sorted set.
            member_score_mapping (dict): Mapping of member to its score.

        Returns:
            dict: A dictionary containing 'success' (bool), 'message' (str), and 'result' (int).
        """
        try:
            if not member_score_mapping:
                module_logger.warning(f"No members provided for ZAdd to sorted set: {set_name}")
                return {'success': False, 'message': 'No members provided', 'result': -1}

            serialized_mapping = {self.serialize_for_redis(member): score
                                  for member, score in member_score_mapping.items()}

            added_count = self.client.zadd(set_name, serialized_mapping)

            module_logger.debug(f"Redis ZAdd to Sorted Set {set_name} <<success>>: Added {added_count} members")

            return {
                'success': True,
                'message': f'Added {added_count} members to sorted set {set_name}',
                'result': added_count
            }

        except redis.RedisError as error:
            error_msg = f"Redis ZAdd to Sorted Set {set_name} <<failed>>, error: {error}"
            module_logger.error(error_msg)
            return {'success': False, 'message': error_msg}

    def zrangebyscore(self, key, min_score, max_score, start=None, num=None):
        """
                Retrieve a range of members from a sorted set by score.

                Args:
                    key (str): The name of the set.
                    min_score (float): Minimum score.
                    max_score (float): Maximum score.
                    start (int, optional): Start index. Defaults to None.
                    num (int, optional): Number of members to retrieve. Defaults to None.

                Returns:
                    dict: A dictionary containing 'success' (bool) and 'message' (str or list).
        """
        try:
            values = self.client.zrangebyscore(key, min_score, max_score, start=start, num=num)
            decoded_values = [self.deserialize_from_redis(value.decode("utf-8")) for value in values]
            module_logger.debug(f"Redis ZRangeByScore Key <<success:>> {key}")
            return {'success': True, 'message': 'success', 'result': decoded_values}
        except redis.RedisError as error:
            error_msg = f"Redis ZRangeByScore Key <<failed:>> {key}, error: {error}"
            module_logger.error(error_msg)
            return {'success': False, 'message': error_msg}

    def zremrangebyscore(self, set_name, min_score, max_score):
        """
        Remove members from a Redis sorted set within a score range.

        Args:
            set_name (str): The name of the sorted set.
            min_score (float): Minimum score.
            max_score (float): Maximum score.

        Returns:
            dict: A dictionary containing 'success' (bool), 'message' (str), and 'result' (int).
        """
        try:
            removed_count = self.client.zremrangebyscore(set_name, min_score, max_score)

            if removed_count:
                module_logger.debug(f"Redis ZRemRangeByScore {set_name} <<success>>: Removed {removed_count} members")
                message = f'Removed {removed_count} members from sorted set {set_name}'
            else:
                module_logger.debug(f"Redis ZRemRangeByScore {set_name}: No members removed")
                message = f'No members were removed from sorted set {set_name}'

            return {
                'success': True,
                'message': message,
                'result': removed_count
            }

        except redis.RedisError as error:
            error_msg = f"Redis ZRemRangeByScore for Sorted Set {set_name} <<failed>>, error: {error}"
            module_logger.error(error_msg)
            return {'success': False, 'message': error_msg}

    def zinterstore(self, dest, keys, aggregate=None):
        """
                Compute the intersection of multiple sorted sets.

                Args:
                    dest (str): Name of the resulting set.
                    keys (list): List of sets to intersect.
                    aggregate (str, optional): Aggregation method. Defaults to None.

                Returns:
                    dict: A dictionary containing 'success' (bool) and 'message' (str).
                """
        try:
            self.client.zinterstore(dest, keys, aggregate=aggregate)
            module_logger.debug(f"Redis ZInterStore Key <<success:>> {dest}")
            return {'success': True, 'message': 'success', 'result': 0}
        except redis.RedisError as error:
            error_msg = f"Redis ZInterStore Key <<failed:>> {dest}, error: {error}"
            module_logger.error(error_msg)
            return {'success': False, 'message': error_msg}

    def keys(self, pattern):
        """
                Find all keys matching a given pattern.

                Args:
                    pattern (str): The pattern to match.

                Returns:
                    dict: A dictionary containing 'success' (bool) and 'message' (str or list).
        """
        try:
            keys = self.client.keys(pattern)
            decoded_keys = [key.decode("utf-8") for key in keys]
            module_logger.debug(f"Redis Keys Pattern <<success:>> {pattern}")
            return {'success': True, 'message': 'success', 'result': decoded_keys}
        except redis.RedisError as error:
            error_msg = f"Redis Keys Pattern <<failed:>> {pattern}, error: {error}"
            module_logger.error(error_msg)
            return {'success': False, 'message': error_msg}

    def expire(self, key, time_in_seconds):
        """
               Set an expiration time on a key.

               Args:
                   key (str): The key to set expiration on.
                   time_in_seconds (int): Expiration time in seconds.

               Returns:
                   dict: A dictionary containing 'success' (bool) and 'message' (str).
               """
        try:
            self.client.expire(key, time_in_seconds)
            module_logger.debug(f"Redis Expire Key <<success:>> {key}")
            return {'success': True, 'message': 'success', 'result': 0}
        except redis.RedisError as error:
            error_msg = f"Redis Expire Key <<failed:>> {key}, error: {error}"
            module_logger.error(error_msg)
            return {'success': False, 'message': error_msg}

    def scan(self, cursor=0, match=None, count=None):
        """
                Incrementally iterate the keys space.

                Args:
                    cursor (int): Cursor position to start from.
                    match (str, optional): Pattern to match. Defaults to None.
                    count (int, optional): Number of keys to return. Defaults to None.

                Returns:
                    dict: A dictionary containing 'success' (bool), 'message' (str or list), and 'cursor' (int).
                """
        try:
            cursor, keys = self.client.scan(cursor, match, count)
            decoded_keys = [self.deserialize_from_redis(key.decode("utf-8")) for key in keys]
            module_logger.debug(f"Redis Scan Pattern <<success>>: {match}")
            return {'success': True, 'cursor': cursor, 'message': 'success', 'result': decoded_keys}
        except redis.RedisError as error:
            error_msg = f"Redis Scan Pattern <<failed>>: {match}, error: {error}"
            module_logger.error(error_msg)
            return {'success': False, 'cursor': None, 'message': error_msg}

    def scan_iter(self, match=None, count=None):
        """
                Generate keys matching a pattern.

                Args:
                    match (str, optional): Pattern to match. Defaults to None.
                    count (int, optional): Number of keys to generate. Defaults to None.

                Returns:
                    dict: A dictionary containing 'success' (bool) and 'message' (str or generator).
                """
        try:
            key_generator = (self.deserialize_from_redis(key.decode("utf-8")) for key in
                             self.client.scan_iter(match, count))
            module_logger.debug(f"Redis Scan_Iter Pattern <<success>>: {match}")
            return {'success': True, 'message': 'success', 'result': key_generator}
        except redis.RedisError as error:
            error_msg = f"Redis Scan_Iter Pattern <<failed>>: {match}, error: {error}"
            module_logger.error(error_msg)
            return {'success': False, 'message': error_msg}

    @staticmethod
    def deserialize_from_redis(value):
        """
        Convert a string value from Redis into its Python data type.

        Args:
            value (str): The string value to deserialize.

        Returns:
            any: The deserialized value in its Python data type.
        """
        # If value is the string "null", return Python's None
        if value == "null":
            return None

        # Try JSON deserialization
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            pass

        # Handle common string representations
        value_lower = value.lower()
        if value_lower == "true":
            return True
        elif value_lower == "false":
            return False
        elif value_lower == "null":
            return None

        # Try parsing as integer
        try:
            return int(value)
        except ValueError:
            pass

        # Try parsing as float
        try:
            return float(value)
        except ValueError:
            pass

        # Try parsing as datetime object
        try:
            return datetime.datetime.fromisoformat(value)
        except ValueError:
            pass

        # Try parsing as date object
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            pass

        # If no other type matched, return the original string
        return value

    @staticmethod
    def serialize_for_redis(data):
        """
        Convert a Python data item to its string representation for Redis storage.

        Args:
            data (any): The Python data item to serialize.

        Returns:
            str: The string representation suitable for Redis storage.
        """
        # Handle simple types
        if data is None:
            return "null"
        if isinstance(data, (str, bytes)):
            return data.decode('utf-8') if isinstance(data, bytes) else data
        if isinstance(data, bool):
            return str(data).lower()
        if isinstance(data, (int, float)):
            return str(data)
        if isinstance(data, datetime.datetime):
            return data.isoformat()
        if isinstance(data, datetime.date):
            return data.isoformat()

        # Handle complex types with JSON serialization
        try:
            return json.dumps(data)
        except (ValueError, TypeError):
            # If can't serialize with JSON, return the string representation
            return str(data)
