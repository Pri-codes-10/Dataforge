import asyncio
import os
import time
from dotenv import load_dotenv
load_dotenv('backend/.env')
from google import genai
from google.genai import types
from pydantic import BaseModel
from typing import Optional

class ToolDecision(BaseModel):
    tool: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    date: Optional[str] = None

async def test():
    client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
    for q in ['Find a flight from Kolkata to Delhi tomorrow', 'Delhi jaana hai tomorrow', 'What is machine learning?', 'What is the weather in Kolkata?']:
        t0 = time.time()
        resp = await client.aio.models.generate_content(
            model='gemini-3.6-flash',
            contents=f'Determine if this query needs a tool (search_flights, search_hotels, search_information) or if it is a general question (null): "{q}"',
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                response_schema=ToolDecision,
                temperature=0.0
            )
        )
        print(f'{q} ({time.time()-t0:.2f}s): {resp.text.strip()}')

if __name__ == '__main__':
    asyncio.run(test())
