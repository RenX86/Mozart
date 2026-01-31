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
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "music_queue" (
                "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                "guild_id" INT,
                "title" TEXT,
                "url" TEXT,
                "thumbnail" TEXT,
                "duration" REAL,
                "requester" TEXT,
                "channel_id" INT,
                "position" INT
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

    # Music Queue Methods
    async def add_to_queue(self, guild_id: int, song_data: dict):
        import asyncio
        import json
        loop = asyncio.get_running_loop()

        def _execute():
            connection = self.get_connection()
            cursor = connection.cursor()
            
            # Get next position
            cursor.execute("SELECT MAX(position) FROM music_queue WHERE guild_id = ?", (guild_id,))
            result = cursor.fetchone()
            next_pos = (result[0] or 0) + 1
            
            # Use JSON to store complex dicts (like channel info which we can't fully store, so we store IDs)
            # For simplicity, we'll store specific fields we need
            
            cursor.execute("""
                INSERT INTO music_queue (guild_id, title, url, thumbnail, duration, requester, channel_id, position)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                guild_id, 
                song_data.get('title'),
                song_data.get('webpage_url'),
                song_data.get('thumbnail'),
                song_data.get('duration'),
                song_data.get('requester'),
                song_data['channel'].id if hasattr(song_data.get('channel'), 'id') else None,
                next_pos
            ))
            
            connection.commit()
            connection.close()
        
        await loop.run_in_executor(None, _execute)

    async def get_queue(self, guild_id: int):
        import asyncio
        loop = asyncio.get_running_loop()

        def _execute():
            connection = self.get_connection()
            connection.row_factory = sqlite3.Row # Allow dict-like access
            cursor = connection.cursor()
            
            cursor.execute("""
                SELECT * FROM music_queue 
                WHERE guild_id = ? 
                ORDER BY position ASC
            """, (guild_id,))
            
            rows = cursor.fetchall()
            
            queue = []
            for row in rows:
                queue.append({
                    'id': row['id'],
                    'title': row['title'],
                    'webpage_url': row['url'],
                    'thumbnail': row['thumbnail'],
                    'duration': row['duration'],
                    'requester': row['requester'],
                    'channel_id': row['channel_id'] 
                    # Note: We return channel_id, the Cog will need to resolve it to an object
                })
            
            connection.close()
            return queue

        return await loop.run_in_executor(None, _execute)

    async def pop_from_queue(self, guild_id: int):
        import asyncio
        loop = asyncio.get_running_loop()

        def _execute():
            connection = self.get_connection()
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()
            
            # Get the first item
            cursor.execute("""
                SELECT * FROM music_queue 
                WHERE guild_id = ? 
                ORDER BY position ASC 
                LIMIT 1
            """, (guild_id,))
            
            row = cursor.fetchone()
            
            if row:
                # Delete it
                cursor.execute("DELETE FROM music_queue WHERE id = ?", (row['id'],))
                connection.commit()
                
                # Retrieve data
                item = {
                    'id': row['id'],
                    'title': row['title'],
                    'webpage_url': row['url'],
                    'thumbnail': row['thumbnail'],
                    'duration': row['duration'],
                    'requester': row['requester'],
                    'channel_id': row['channel_id']
                }
                connection.close()
                return item
            
            connection.close()
            return None

        return await loop.run_in_executor(None, _execute)

    async def clear_queue(self, guild_id: int):
        import asyncio
        loop = asyncio.get_running_loop()

        def _execute():
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute("DELETE FROM music_queue WHERE guild_id = ?", (guild_id,))
            connection.commit()
            connection.close()

        await loop.run_in_executor(None, _execute)
        
    async def shuffle_queue(self, guild_id: int):
        import asyncio
        import random
        loop = asyncio.get_running_loop()

        def _execute():
            connection = self.get_connection()
            cursor = connection.cursor()
            
            # Get all IDs for this guild
            cursor.execute("SELECT id FROM music_queue WHERE guild_id = ? ORDER BY position ASC", (guild_id,))
            ids = [row[0] for row in cursor.fetchall()]
            
            if not ids:
                connection.close()
                return

            # Shuffle the positions, but keep IDs the same (effectively reordering)
            # Actually, simpler: just shuffle the order of IDs and re-assign positions 1..N
            random.shuffle(ids)
            
            for index, row_id in enumerate(ids):
                cursor.execute("UPDATE music_queue SET position = ? WHERE id = ?", (index + 1, row_id))
            
            connection.commit()
            connection.close()

        await loop.run_in_executor(None, _execute)
