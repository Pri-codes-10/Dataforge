import json
import unittest
from app.gemini_planner import GeminiPlanner, GeminiError


class Response:
    def __init__(self, data, status=200):
        self.data, self.status = data, status
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def json(self): return self.data


class Client:
    def __init__(self, response): self.response = response
    def post(self, url, **kwargs):
        self.url, self.kwargs = url, kwargs
        return self.response


class GeminiTests(unittest.IsolatedAsyncioTestCase):
    async def test_mixed_transcript_and_validated_delta(self):
        plan = dict(kind='call_tool', changes=[dict(key='max_price',value=6000)],
                    text='Checking.', tool='search', new_intent=False, reset_constraints=False)
        client = Client(Response({'candidates':[{'finishReason':'STOP', 'content':{
            'parts':[{'text':json.dumps(plan)}]}}]}))
        result = await GeminiPlanner(client,'gemini-2.5-flash','test-placeholder').plan(
            'छह हजार se kam', {'destination':'Delhi'}, {'active_tool_count':1})
        self.assertEqual(result.changes, {'max_price':6000})
        payload = json.loads(client.kwargs['json']['contents'][0]['parts'][0]['text'])
        self.assertEqual(payload['transcript'], 'छह हजार se kam')
        self.assertEqual(payload['constraints'], {'destination':'Delhi'})
        self.assertNotIn('test-placeholder', client.url)

    async def test_http_error_does_not_expose_body_or_key(self):
        client = Client(Response({'error':'sensitive provider detail'},429))
        with self.assertRaises(GeminiError) as caught:
            await GeminiPlanner(client,'gemini-2.5-flash','test-placeholder').plan('',{}, {})
        self.assertEqual(caught.exception.status_code,429)
        self.assertNotIn('sensitive',str(caught.exception))

    async def test_blocked_response_is_rejected(self):
        with self.assertRaises(ValueError):
            await GeminiPlanner(Client(Response({'candidates':[]})),
                                'gemini-2.5-flash','test-placeholder').plan('',{}, {})

    async def test_invalid_budget_is_rejected(self):
        plan = dict(kind='call_tool', changes=[dict(key='max_price',value=-5)],
                    text='Checking.',tool='search',new_intent=False,reset_constraints=False)
        client=Client(Response({'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(plan)}]}}]}))
        with self.assertRaises(ValueError):
            await GeminiPlanner(client,'gemini-2.5-flash','test-placeholder').plan('',{}, {})
