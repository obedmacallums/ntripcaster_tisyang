import trio
import logging

try:
    from pycaster.tokens import prepare_tokens, match_token
    from pycaster.protocol import parse_request
except ImportError:
    # If running directly, try relative imports
    from tokens import prepare_tokens, match_token
    from protocol import parse_request


async def send_source_table(stream, sources, lock):
    """Send NTRIP source table to client."""
    async with lock:
        active_sources = list(sources.keys())
    
    # Build the table content first, matching the C implementation format
    table_content = ""
    for mount in active_sources:
        # Format matching the C code: STR;mount;mount;RTCM3X;1005(10),1074-1084-1124(1);2;GNSS;NET;CL;0.00;0.00;1;1;None;None;B;N;0;
        table_content += f"STR;{mount};{mount};RTCM3X;1005(10),1074-1084-1124(1);2;GNSS;NET;CL;0.00;0.00;1;1;None;None;B;N;0;\r\n"
    
    table_content += "ENDSOURCETABLE\r\n"
    
    # Build the NTRIP response (not HTTP), matching the C implementation
    import time
    from datetime import datetime
    
    now = datetime.utcnow()
    timestr = now.strftime("%a %b %d %H:%M:%S %Y")
    content_length = len(table_content.encode('utf-8'))
    
    response = f"SOURCETABLE 200 OK\r\n"
    response += f"Server: https://github.com/tisyang/ntripcaster.git\r\n"
    response += f"Date: {timestr} UTC\r\n"
    response += f"Connection: close\r\n"
    response += f"Content-Type: text/plain\r\n"
    response += f"Content-Length: {content_length}\r\n"
    response += f"\r\n"
    response += table_content
    
    await stream.send_all(response.encode('utf-8'))


async def handle_agent(stream, cfg, client_tokens, source_tokens, clients, sources, lock):
    addr = stream.socket.getpeername()
    logging.info("Connection from %s", addr)
    data = b''
    while b'\r\n\r\n' not in data:
        chunk = await stream.receive_some(1024)
        if not chunk:
            logging.info("Connection closed before headers from %s", addr)
            return
        data += chunk
        if len(data) > 4096:
            logging.warning("Header too large from %s", addr)
            return
    req = parse_request(data)
    if not req:
        logging.warning("Malformed request from %s", addr)
        await stream.aclose()
        return
    mount = req['mountpoint']
    if req['type'] == 'client':
        # Check if the requested mountpoint exists
        async with lock:
            has_mountpoint = mount and mount in sources
        
        # If no mountpoint specified, empty, root path, or mountpoint doesn't exist, send source table
        if not mount or mount == '' or mount == '/' or not has_mountpoint:
            logging.info("Client requesting source table from %s (mountpoint: '%s')", addr, mount)
            await send_source_table(stream, sources, lock)
            await stream.aclose()
            return
        
        token = req['auth'].split()[-1] if req['auth'] else ''
        if not match_token(client_tokens, token, mount):
            logging.warning("Client auth failed for mount %s from %s", mount, addr)
            await stream.send_all(b"HTTP/1.0 401 Unauthorized\r\n\r\n")
            await stream.aclose()
            return
        
        async with lock:
            clients.setdefault(mount, set()).add(stream)
        await stream.send_all(b"ICY 200 OK\r\n")
        logging.info("Client connected to %s from %s", mount, addr)
        try:
            while True:
                if await stream.receive_some(1024) == b'':
                    break
        finally:
            async with lock:
                clients[mount].discard(stream)
            await stream.aclose()
        logging.info("Client disconnected from %s (%s)", mount, addr)
    elif req['type'] == 'source':
        if not match_token(source_tokens, req['passwd'], mount):
            logging.warning("Source auth failed for mount %s from %s", mount, addr)
            await stream.send_all(b"ERROR - Bad Password\r\n")
            await stream.aclose()
            return
        async with lock:
            if mount in sources:
                logging.warning("Mountpoint %s already in use from %s", mount, addr)
                await stream.send_all(b"ERROR - Bad Mountpoint\r\n")
                await stream.aclose()
                return
            sources[mount] = stream
        await stream.send_all(b"ICY 200 OK\r\n")
        logging.info("Source connected to %s from %s", mount, addr)
        try:
            while True:
                data = await stream.receive_some(8192)
                if not data:
                    break
                async with lock:
                    for client in list(clients.get(mount, [])):
                        try:
                            await client.send_all(data)
                        except Exception:
                            clients[mount].discard(client)
        finally:
            async with lock:
                sources.pop(mount, None)
            await stream.aclose()
        logging.info("Source disconnected from %s (%s)", mount, addr)


async def run_server(cfg):
    client_tokens = prepare_tokens(cfg['tokens_client'])
    source_tokens = cfg['tokens_source']
    clients = {}
    sources = {}
    lock = trio.Lock()
    listeners = await trio.open_tcp_listeners(cfg['listen_port'], host=cfg['listen_addr'])
    logging.info('Listening on %s:%s', cfg['listen_addr'], cfg['listen_port'])
    async with trio.open_nursery() as nursery:
        for lst in listeners:
            nursery.start_soon(trio.serve_listeners, lambda s: handle_agent(s, cfg, client_tokens, source_tokens, clients, sources, lock), [lst])
