import sqlite3
import os

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.create_user_table()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def create_user_table(self):
        connection = self.get_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "users_per_guild" (
                "user_id" INT,
                "warnings_count" INT,
                "guild_id" INT,
                PRIMARY KEY("user_id","guild_id")
            )
        """)
        connection.commit()
        connection.close()

    async def increase_and_get_warnings(self, user_id: int, guild_id: int):
        import asyncio
        loop = asyncio.get_running_loop()
        
        def _execute():
            connection = self.get_connection()
            cursor = connection.cursor()
            
            cursor.execute("""
                SELECT warnings_count
                FROM users_per_guild
                WHERE (user_id = ?) AND (guild_id = ?);               
            """,(user_id, guild_id))
            
            result = cursor.fetchone()
            
            if result == None:
                cursor.execute("""
                   INSERT INTO users_per_guild (user_id, warnings_count, guild_id)
                   VALUES (?,1,?);            
                """, (user_id, guild_id))
                
                new_warnings = 1
            else:
                new_warnings = result[0] + 1
                cursor.execute("""
                    UPDATE users_per_guild
                    SET warnings_count = ?
                    WHERE (user_id = ?) AND (guild_id = ?);      
                    """,(new_warnings, user_id, guild_id)) 
            
            connection.commit()
            connection.close()
            return new_warnings

        return await loop.run_in_executor(None, _execute)
