import json


from aiohttp import web


from models import Session, Adv, engine, init_orm

app = web.Application()


async def init_db(app: web.Application):
    print("START")
    await init_orm()
    yield
    print("FINISH")
    await engine.dispose()


@web.middleware
async def session_middleware(request: web.Request,
                             handler):
    async with Session() as session:
        request.session = session
        response = await handler(request)
        return response


app.cleanup_ctx.append(init_db)
app.middlewares.append(session_middleware)


def get_http_error(error_class, message):
    return error_class(
        text=json.dumps({"error": message}), content_type="application/json"
    )


async def get_adv_by_id(session: Session, adv_id: int):
    adv = await session.get(Adv, adv_id)
    if adv is None:
        raise get_http_error(web.HTTPNotFound,
                             f"ads with the id {adv_id} not found")
    return adv


async def add_adv(session: Session, adv: Adv):
    session.add(adv)
    await session.commit()
    print(adv)
    return adv


class AdvView(web.View):

    @property
    def session(self) -> Session:
        return self.request.session

    @property
    def adv_id(self):
        return int(self.request.match_info[
                    "adv_id"])

    async def get_adv(self):
        return await get_adv_by_id(self.session, self.adv_id)

    async def get(self):
        adv = await self.get_adv()
        return web.json_response(adv.dict)

    async def post(self):
        json_data = await self.request.json()
        adv = Adv(**json_data)
        await add_adv(self.session, adv)
        return web.json_response({"id": adv.id})

    async def patch(self):
        json_data = await self.request.json()
        adv = await self.get_adv()
        for field, value in json_data.items():
            setattr(adv, field, value)
        await add_adv(self.session, adv)
        return web.json_response(adv.dict)

    async def delete(self):
        adv = await self.get_adv()
        await self.session.delete(adv)
        await self.session.commit()
        return web.json_response({"status": "deleted"})


app.add_routes(
    [
        web.get("/api/{adv_id:\d+}", AdvView),
        web.patch("/api/{adv_id:\d+}", AdvView),
        web.delete("/api/{adv_id:\d+}", AdvView),
        web.post("/api", AdvView),
    ]
)

web.run_app(app, port=8080)
