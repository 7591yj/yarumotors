import httpx


async def notify_bot(worker_domain):
    async with httpx.AsyncClient() as client:
        resp = await client.post(worker_domain + "update")
        resp.raise_for_status()
