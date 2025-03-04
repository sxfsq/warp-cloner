import random
from typing import Any, Optional, TypedDict

from aiohttp import ClientResponse, ClientSession, ClientTimeout
# from aiohttp_socks import ProxyConnector    下载到本地使用时应将此行注释


BASE_URL: str = 'https://api.cloudflareclient.com'
BASE_HEADERS: dict[str, str] = {
    'User-Agent': 'okhttp/3.12.1',
}


class RegisterDataAccount(TypedDict):
    id: str
    account_type: str
    created: str # date in ISO 8601 format
    updated: str # date in ISO 8601 format
    premium_data: int
    quota: int
    usage: int
    warp_plus: int
    refferal_count: int
    referral_renewal_countdown: int
    role: str
    license: str


class RegisterData(TypedDict):
    id: str
    type: str
    name: str
    key: str # base64 encoded
    account: RegisterDataAccount
    config: Any # we don't use it, so i think it's acceptable to use any
    token: str
    warp_enabled: bool
    waitlist_enabled: bool
    created: str # date in ISO 8601 format
    updated: str # date in ISO 8601 format
    tos: str # date in ISO 8601 format
    place: int
    locale: str
    enabled: bool
    install_id: str
    fcm_token: str


class GetInfoData(TypedDict):
    id: str
    account_type: str
    created: str # date in ISO 8601 format
    updated: str # date in ISO 8601 format
    premium_data: int
    quota: int
    warp_plus: bool
    referral_count: int
    referral_renewal_countdown: int
    role: str
    license: str


async def register(path: str, session: ClientSession, data: dict[str, str] = {}) -> RegisterData:
    response: ClientResponse = await session.post(
        '/{}/reg'.format(path),
        headers={
            'Content-Type': 'application/json; charset=UTF-8',
            **BASE_HEADERS,
        },
        json=data
    )

    if response.status != 200:
        match response.status:
            case 403:
                response_text: str = 'Access denied, proxy or your IP is probably blocked on API'
            case 429:
                response_text: str = 'Too Many Requests, too much keys was generated for last minute from this proxy or your IP'
            case _:
                response_text: str =  await response.text()

        response.close()
        raise Exception('Failed to register: {} {}'.format(response.status, response_text))

    json: RegisterData = await response.json()

    return json


async def add_key(path: str, session: ClientSession, reg_id: str, token: str, key: str) -> None:
    response: ClientResponse = await session.put(
        '/{}/reg/{}/account'.format(path, reg_id),
        headers={
            'Authorization': 'Bearer {}'.format(token),
            'Content-Type': 'application/json; charset=UTF-8',
            **BASE_HEADERS,
        },
        json={
            'license': key,
        }
    )

    if response.status != 200:
        response_text = await response.text()
        response.close()
        raise Exception('Failed to add key: {} {}'.format(response.status, response_text))


async def delete_account(path: str, session: ClientSession, reg_id: str, token: str) -> None:
    response: ClientResponse = await session.delete(
        '/{}/reg/{}'.format(path, reg_id),
        headers={
            'Authorization': 'Bearer {}'.format(token),
            **BASE_HEADERS,
        }
    )

    if response.status != 204:
        response.close()
        raise Exception('Failed to delete account: {}'.format(response.status))


async def get_account(path: str, session: ClientSession, reg_id: str, token: str) -> GetInfoData:
    response: ClientResponse = await session.get(
        '/{}/reg/{}/account'.format(path, reg_id),
        headers={
            'Authorization': 'Bearer {}'.format(token),
            **BASE_HEADERS,
        }
    )

    if response.status != 200:
        response_text = await response.text()
        response.close()
        raise Exception('Failed to get account: {} {}'.format(response.status, response_text))

    json: GetInfoData = await response.json()

    return json


async def clone_key(key: str, proxy_url: Optional[str], device_model: Optional[str]) -> GetInfoData:
    connector: ProxyConnector | None = ProxyConnector.from_url(
        proxy_url
    ) if proxy_url else None

    path: str = 'v0a{}'.format(
        random.randint(100, 999)
    )

    base_url: str = BASE_URL

    timeout: ClientTimeout = ClientTimeout(total=15)

    async with ClientSession(connector=connector, timeout=timeout, base_url=base_url) as session:
        register_body: dict[str, str] = {}

        if device_model:
            register_body['type'] = 'Android'
            register_body['model'] = device_model

        register_data: RegisterData = await register(path, session, register_body)

        refferer_body: dict[str, str] = {
            'referrer': register_data['id'],
        }

        await register(path, session, refferer_body)

        await add_key(path, session, register_data['id'], register_data['token'], key)
        await add_key(path, session, register_data['id'], register_data['token'], register_data['account']['license'])

        information: GetInfoData = await get_account(path, session, register_data['id'], register_data['token'])

        if not device_model:
            await delete_account(path, session, register_data['id'], register_data['token'])

        return information

