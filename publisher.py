import aiomqtt
import asyncio
import random
import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

mqtt_host = os.getenv("MQTT_BROKER_HOST")
mqtt_port = int(os.getenv("MQTT_BROKER_PORT"))

async def publish_ff(client):
	while True:
		topic_ff = random.randrange(10,100)
		await client.publish("FF-FF-FF", payload=str(topic_ff))
		await asyncio.sleep(random.randrange(1,4))

async def publish_aa(client):
	while True:
		topic_aa = random.randrange(20,40)
		await client.publish("AA-AA-AA", payload=str(topic_aa))
		await asyncio.sleep(random.randrange(1,4))

async def publish_dd(client):
	while True:
		topic_dd = random.randrange(100,130)
		await client.publish("DD-DD-DD", payload=str(topic_dd))
		await asyncio.sleep(random.randrange(1,4))

async def start_publisher():
	async with aiomqtt.Client(hostname=mqtt_host, port=mqtt_port) as client:
		await asyncio.gather(
            publish_ff(client),
            publish_aa(client),
            publish_dd(client)
        )


