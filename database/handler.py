import pymongo
import asyncio

class DatabaseConnection(pymongo.MongoClient):
    def __init__(self):
        super().__init__("mongodb://localhost:27017/")
        self._database = self['db_main3']
        self._guild_data = self.load_collection("guild_data")
        self._active_webhooks = self.load_collection("active_webhooks")
        self._emoji_holding_servers = self.load_collection("emoji_holding_servers")

    def load_collection(self, name):
        return self._database[name]

    def add_webhook(self, channel_id, webhook_id):
        document = {
            "channel_id": channel_id,
            "webhook_id": webhook_id
        }
        self._active_webhooks.insert_one(document)
    
    def get_webhook(self, channel_id):
        return self._active_webhooks.find_one({"channel_id": channel_id})

    def remove_webhook(self, channel_id):
        document = {
            "channel_id": channel_id,
        }
        self._active_webhooks.delete_one(document)

    def add_emoji_holding_server(self, guild_id):
        document = {
            "_id": self._emoji_holding_servers.count_documents({})+1,
            "guild_id": guild_id,
        }
        self._emoji_holding_servers.insert_one(document)
    
    def get_emoji_holding_server(self):
        if self._emoji_holding_servers.count_documents({}) > 0:
            return self._emoji_holding_servers.find().sort('_id',-1).limit(1).next()["guild_id"]
        else:
            return None

    def remove_emoji_holding_server(self, guild_id):
        document = {
            "guild_id": guild_id,
        }
        self._emoji_holding_servers.delete_one(document)    