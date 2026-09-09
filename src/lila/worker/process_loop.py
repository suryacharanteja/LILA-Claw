"""Independent worker liveness and bounded local document extraction."""
import asyncio
from lila.runtime.worker_http import async_client
from lila.worker.documents import extract
from lila.worker.task_loop import tasks


async def heartbeat(client):
    while True:
        response=await client.post('/internal/v1/health',json={})
        response.raise_for_status()
        await asyncio.sleep(2)


async def documents(client):
    while True:
        response=await client.post('/internal/v1/documents/next',json={})
        response.raise_for_status()
        assignment=response.json()
        if not assignment['available']:
            await asyncio.sleep(1)
            continue
        operation=assignment['operation_id']
        data=bytearray()
        async with client.stream('GET',f'/internal/v1/documents/{operation}/data') as source:
            source.raise_for_status()
            async for chunk in source.aiter_bytes():
                data.extend(chunk)
                if len(data)>100*1024*1024:
                    raise ValueError('document size limit')
        try:
            result=await asyncio.wait_for(asyncio.to_thread(extract,bytes(data),assignment['media_type']),60)
        except TimeoutError:
            raise
        except Exception:
            result={'text':'','proposals':[],'status':'FAILED'}
        finally:
            data.clear()
        response=await client.post(f'/internal/v1/documents/{operation}/result',json=result)
        response.raise_for_status()


async def run(boot):
    async with async_client(boot) as client:
        async with asyncio.TaskGroup() as group:
            group.create_task(heartbeat(client))
            group.create_task(documents(client))
            group.create_task(tasks(client))
