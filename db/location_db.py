from typing import Optional

from db.connections import ConnectionManager

class LocationCommands:
    def __init__(self, connection: Optional[ConnectionManager] = None):
        self.connection = connection or ConnectionManager()
        self.location_db = self.connection.get_location_db()
        self.locations_collection = self.location_db['locations']

    async def get_locations(self):
        locations = []
        try:
            cursor = self.locations_collection.find({}, {'_id': 0})
            async for document in cursor:
                locations.append(document)
        except Exception as e:
            print(f'Error fetching locations: {e}')
            raise
        return locations
    
    async def get_location_by_id(self, location_id):
        return await self.locations_collection.find_one({'locationId': location_id}, {'_id': 0})